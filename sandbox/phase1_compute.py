#!/usr/bin/env python3
import argparse
import math
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.utils.data import DataLoader, TensorDataset
from datasets import load_dataset

SEED = 2026
DEVICE = torch.device('cpu')
SEQ_LEN = 64
BATCH_SIZE = 32
LAYERS = 12
EMBED_DIM = 128
BASE_LR = 1e-3
WEIGHT_DECAY = 1e-4
MAX_TOKENS = 1_000_000
EVAL_INTERVAL = 20_480
TARGET_PPL = 22.0

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


def build_dataset(limit=8192):
    ds = load_dataset('wikitext', 'wikitext-2-raw-v1', split='train[:4%]')
    text = '\n'.join(ds['text'][:250])
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

class PolicyMLP(nn.Module):
    def __init__(self, hidden=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1)
        )

    def forward(self, features):
        x = self.net(features)
        x = torch.sigmoid(x)
        multiplier = 0.8 + x * 0.6  # between 0.8 and 1.4
        return multiplier.squeeze(-1)


def run_phase(opt_name, seed):
    torch.manual_seed(seed)
    dataset, vocab_size = build_dataset()
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    model = MiniTransformer(vocab_size).to(DEVICE)

    if opt_name == 'ES':
        optimizer = AdamW(model.parameters(), lr=BASE_LR, weight_decay=WEIGHT_DECAY)
        policy = None
    else:
        layer_groups = [
            {'params': layer.parameters(), 'layer_id': f'layer_{i}'}
            for i, layer in enumerate(model.transformer.layers)
        ]
        layer_groups.append({'params': model.embed.parameters(), 'layer_id': 'embed'})
        layer_groups.append({'params': model.out.parameters(), 'layer_id': 'out'})
        optimizer = AdamW(layer_groups, lr=BASE_LR, weight_decay=WEIGHT_DECAY)
        policy = PolicyMLP()

    tokens_seen = 0
    evaluations = []
    target_reached = None
    prev_loss = None
    start_time = time.time()
    data_iter = iter(loader)

    while tokens_seen < MAX_TOKENS:
        try:
            x, y = next(data_iter)
        except StopIteration:
            data_iter = iter(loader)
            x, y = next(data_iter)
        x = x.to(DEVICE)
        y = y.to(DEVICE)
        optimizer.zero_grad()
        logits = model(x)
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
        loss.backward()
        tokens_seen += x.numel()
        if policy is not None:
            if prev_loss is None:
                loss_delta = 0.0
            else:
                loss_delta = loss.item() - prev_loss
            prev_loss = loss.item()
            for idx, group in enumerate(optimizer.param_groups):
                lid = group.get('layer_id', f'group_{idx}')
                grad_norm = math.sqrt(sum(p.grad.norm().item() ** 2 for p in group['params'] if p.grad is not None))
                weight_norm = math.sqrt(sum(p.data.norm().item() ** 2 for p in group['params']))
                features = torch.tensor([grad_norm, weight_norm, loss_delta], device=DEVICE).unsqueeze(0)
                multiplier = policy(features).item()
                group['lr'] = BASE_LR * multiplier
        optimizer.step()
        if tokens_seen >= EVAL_INTERVAL or tokens_seen >= MAX_TOKENS:
            val_loss = evaluate(model, dataset)
            val_ppl = math.exp(val_loss)
            elapsed = time.time() - start_time
            record = {
                'tokens': tokens_seen,
                'val_loss': val_loss,
                'val_ppl': val_ppl,
                'wall_time': elapsed
            }
            evaluations.append(record)
            if target_reached is None and val_ppl <= TARGET_PPL:
                target_reached = {'tokens': tokens_seen, 'wall_time': elapsed}
            if val_ppl <= TARGET_PPL:
                break
            if tokens_seen >= MAX_TOKENS:
                break
    total_time = time.time() - start_time
    final_loss = evaluate(model, dataset)
    final_ppl = math.exp(final_loss)
    result = {
        'optimizer': opt_name,
        'seed': seed,
        'final_ppl': final_ppl,
        'tokens': tokens_seen,
        'wall_time': total_time,
        'target': target_reached,
        'evaluations': evaluations,
    }
    if policy is not None:
        result['policy_outputs'] = {
            group.get('layer_id', f'group_{idx}'): group['lr'] / BASE_LR
            for idx, group in enumerate(optimizer.param_groups)
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--optimizer', choices=['ES', 'reflective'], required=True)
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()
    result = run_phase(args.optimizer, args.seed)
    print(result)

if __name__ == '__main__':
    main()
