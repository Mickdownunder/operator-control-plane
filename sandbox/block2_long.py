#!/usr/bin/env python3
import argparse
import math
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.utils.data import DataLoader, TensorDataset
from lion_pytorch import Lion
from datasets import load_dataset

DEVICE = torch.device('cpu')
SEQ_LEN = 64
BATCH_SIZE = 32
LAYERS = 12
EMBED_DIM = 128
BASE_LR = 1e-3
WEIGHT_DECAY = 1e-4
SEQUENCE_LIMIT = 8192
TARGET_PPL = 23.30
TARGET_TOKENS = 500000
EVAL_INTERVAL_TOKENS = 20000

class MiniTransformer(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, EMBED_DIM)
        self.pos = nn.Embedding(SEQ_LEN, EMBED_DIM)
        layer = nn.TransformerEncoderLayer(EMBED_DIM, 4, 256, dropout=0.1)
        self.transformer = nn.TransformerEncoder(layer, num_layers=LAYERS)
        self.out = nn.Linear(EMBED_DIM, vocab_size)

    def forward(self, x):
        b, t = x.shape
        pos = torch.arange(t, device=x.device).unsqueeze(0).expand(b, -1)
        h = self.embed(x) + self.pos(pos)
        h = h.transpose(0, 1)
        h = self.transformer(h)
        h = h.transpose(0, 1)
        return self.out(h)


def build_dataset(limit=SEQUENCE_LIMIT):
    ds = load_dataset('wikitext', 'wikitext-2-raw-v1', split='train[:5%]')
    text = '\n'.join(ds['text'][:300])
    chars = sorted({c for line in text for c in line})
    stoi = {ch: i for i, ch in enumerate(chars)}
    tokens = [stoi[c] for c in text if c in stoi]
    sequences = []
    for i in range(len(tokens) - SEQ_LEN):
        chunk = tokens[i:i + SEQ_LEN]
        target = tokens[i + 1:i + SEQ_LEN + 1]
        sequences.append((chunk, target))
    inputs = torch.tensor([s[0] for s in sequences], dtype=torch.long)
    targets = torch.tensor([s[1] for s in sequences], dtype=torch.long)
    if inputs.size(0) > limit:
        inputs = inputs[:limit]
        targets = targets[:limit]
    return TensorDataset(inputs, targets), len(stoi)


def evaluate(model, dataset):
    model.eval()
    loader = DataLoader(dataset, batch_size=BATCH_SIZE)
    total = 0.0
    tokens = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(DEVICE)
            y = y.to(DEVICE)
            logits = model(x)
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
            total += loss.item() * x.numel()
            tokens += x.numel()
    return total / max(1, tokens)


def compute_grad_norm(model):
    return math.sqrt(sum(p.grad.norm().item() ** 2 for p in model.parameters() if p.grad is not None))


def compute_update_norm(pre, post):
    accum = 0.0
    for a, b in zip(pre, post):
        diff = (b - a).detach()
        accum += diff.norm().item() ** 2
    return math.sqrt(accum)


def tokens_to_flops(tokens):
    return tokens * SEQ_LEN * EMBED_DIM * 2 * LAYERS


def run_long(opt_name, seed):
    torch.manual_seed(seed)
    dataset, vocab_size = build_dataset()
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    model = MiniTransformer(vocab_size).to(DEVICE)
    if opt_name == 'ES':
        optimizer = AdamW(model.parameters(), lr=BASE_LR, weight_decay=WEIGHT_DECAY)
        policy_type = 'es'
    else:
        layer_groups = []
        for idx, layer in enumerate(model.transformer.layers):
            layer_groups.append({'params': layer.parameters(), 'layer_id': f'layer_{idx}'})
        layer_groups.append({'params': model.embed.parameters(), 'layer_id': 'embed'})
        layer_groups.append({'params': model.out.parameters(), 'layer_id': 'out'})
        optimizer = AdamW(layer_groups, lr=BASE_LR, weight_decay=WEIGHT_DECAY)
        policy_type = 'reflective'

    tokens_seen = 0
    grad_norms = []
    update_norms = []
    divergences = 0
    policy_outputs = {}
    policy_inputs = []
    evaluations = []
    target_hit = None
    layer_multipliers = {group.get('layer_id', f'group_{i}'): 1.0 for i, group in enumerate(optimizer.param_groups)}
    threshold = 1.1
    scale = 0.35
    next_eval_at = EVAL_INTERVAL_TOKENS
    start_time = time.time()
    iterator = iter(loader)

    while tokens_seen < TARGET_TOKENS:
        try:
            x, y = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            x, y = next(iterator)
        x = x.to(DEVICE)
        y = y.to(DEVICE)
        optimizer.zero_grad()
        logits = model(x)
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
        loss.backward()
        grad_norm = compute_grad_norm(model)
        grad_norms.append(grad_norm)
        pre_params = [p.detach().clone() for p in model.parameters() if p.requires_grad]
        optimizer.step()
        post_params = [p.detach() for p in model.parameters() if p.requires_grad]
        update_norm = compute_update_norm(pre_params, post_params)
        update_norms.append(update_norm)
        if torch.isnan(loss) or torch.isinf(loss):
            divergences += 1
        tokens_seen += x.numel()
        if policy_type == 'es':
            if grad_norm > threshold:
                for group in optimizer.param_groups:
                    group['lr'] *= (1 + scale)
            else:
                for group in optimizer.param_groups:
                    group['lr'] = max(1e-6, group['lr'] * 0.995)
        elif policy_type == 'reflective':
            layer_grads = []
            for group in optimizer.param_groups:
                acc = 0.0
                cnt = 0
                for p in group['params']:
                    if p.grad is not None:
                        acc += p.grad.norm().item() ** 2
                        cnt += 1
                if cnt:
                    acc = math.sqrt(acc)
                layer_grads.append(acc)
            policy_inputs.append(layer_grads)
            for idx, group in enumerate(optimizer.param_groups):
                lid = group.get('layer_id', f'group_{idx}')
                val = layer_grads[idx]
                if val > threshold:
                    layer_multipliers[lid] *= 1 + scale
                else:
                    layer_multipliers[lid] *= 0.98
                group['lr'] = BASE_LR * layer_multipliers[lid]
            policy_outputs = layer_multipliers.copy()
        if tokens_seen >= next_eval_at or tokens_seen >= TARGET_TOKENS:
            val_loss = evaluate(model, dataset)
            val_ppl = math.exp(val_loss)
            elapsed = time.time() - start_time
            eval_record = {
                'tokens': tokens_seen,
                'val_loss': val_loss,
                'val_ppl': val_ppl,
                'wall_time': elapsed,
            }
            evaluations.append(eval_record)
            if target_hit is None and val_ppl <= TARGET_PPL:
                target_hit = {'tokens': tokens_seen, 'wall_time': elapsed}
            next_eval_at += EVAL_INTERVAL_TOKENS
        if tokens_seen >= 200000 and policy_type == 'reflective' and len(evaluations) >= 2:
            if evaluations[-1]['val_ppl'] >= evaluations[-2]['val_ppl']:
                pass
    duration = time.time() - start_time
    val_loss = evaluate(model, dataset)
    val_ppl = math.exp(val_loss)
    final = {
        'optimizer': opt_name,
        'seed': seed,
        'val_loss': val_loss,
        'val_ppl': val_ppl,
        'tokens': tokens_seen,
        'wall_time': duration,
        'flops_proxy': tokens_to_flops(tokens_seen),
        'avg_grad_norm': sum(grad_norms) / max(1, len(grad_norms)),
        'avg_update_norm': sum(update_norms) / max(1, len(update_norms)),
        'divergences': divergences,
        'policy_outputs': policy_outputs,
        'policy_diversity': math.sqrt(sum((v - (sum(layer_multipliers.values()) / len(layer_multipliers))) ** 2 for v in layer_multipliers.values()) / max(1, len(layer_multipliers))) if policy_outputs else None,
        'targets': target_hit,
        'evaluations': evaluations,
        'policy_type': policy_type,
    }
    return final


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--optimizer', choices=['ES', 'reflective'], required=True)
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()
    result = run_long(args.optimizer, args.seed)
    print(result)

if __name__ == '__main__':
    main()
