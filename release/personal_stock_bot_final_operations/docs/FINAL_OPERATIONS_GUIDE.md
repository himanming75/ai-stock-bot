# Personal AI Stock Bot — Final Operations Guide

## Purpose

This package does not add trading logic. It wraps the existing local Personal
Control Center and Validation Scheduler in four external PowerShell launchers.

## Daily Commands

Start:
`powershell -NoProfile -ExecutionPolicy Bypass -File .\START_PERSONAL_STOCK_BOT.ps1`

Status:
`powershell -NoProfile -ExecutionPolicy Bypass -File .\STATUS_PERSONAL_STOCK_BOT.ps1`

Stop:
`powershell -NoProfile -ExecutionPolicy Bypass -File .\STOP_PERSONAL_STOCK_BOT.ps1`

Recover:
`powershell -NoProfile -ExecutionPolicy Bypass -File .\RECOVER_PERSONAL_STOCK_BOT.ps1`

## START behavior

- prevents a duplicate 8770 Control Center from being started;
- starts the existing 8770 Control Center only when absent;
- waits for `/api/daily-ops`;
- ensures the Validation Scheduler is running;
- saves a startup Operations Snapshot;
- does not start Paper trading or submit orders.

## STOP behavior

- saves a final Operations Snapshot;
- requests Validation Scheduler stop;
- stops the 8770 Control Center process;
- does not alter trading strategy, risk, or broker configuration.

## RECOVER behavior

- checks for a stale Validation RUN.lock and only removes it when its owner PID is dead;
- restarts 8770 if missing;
- confirms Daily Ops API health;
- ensures Validation Scheduler is running;
- saves a recovery snapshot.

## Safety

- E*TRADE remains deferred;
- no broker-network action is added;
- no Paper order submission;
- no Live order submission;
- no automatic strategy/model/threshold promotion;
- all process-control actions remain local to the PC.

## Current validation program

The current Validation Lab remains the source of truth for:
- trading-day progress;
- resolved outcomes;
- AI Health;
- Paper Qualification;
- Final Validation Qualification.
