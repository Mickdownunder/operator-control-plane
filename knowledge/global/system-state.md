# Operator System State

## Repository Layout
- Base: repository root configured by environment
- Jobs: job state directory under the configured base path
- Workflows: workflow scripts under the configured base path
- Tools: operator tool scripts under the configured base path
- Knowledge: knowledge documents under the configured base path

## Scheduling
- Recurring automation may run selected workflows in a deployment-defined schedule

## Core Workflows
- infra-status
- signals
- propose-infra
- autopilot-infra
- knowledge-commit
- goal-progress
- planner
- prioritize
- critic

## Tool Factory
- tool-idea
- tool-create
- tool-register
- tool-use
- tool-eval
- tool-improve
- tool-backlog-add
- tool-backlog-improve

## Policy
- policy configuration is environment-defined; default mode is READ_ONLY
