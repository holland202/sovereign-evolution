# SENTINEL — Autonomous Critical Infrastructure Defense

Zero-cloud geometric anomaly detection for ICS/SCADA.
Document ID: SENTINEL-WP-1.0 | Author: Chad Edward Holland | June 2026

## The Problem

Signature systems fail against nation-state ICS attacks because:
- Require cloud connectivity for updates
- Cannot detect zero-day exploits
- Fail against slow-ramp evasion attacks
- Designed for IT not OT

CISA AA26-097A confirmed Iranian APT actors manipulating PLC project
files and SCADA displays across US water, energy, and government sectors.

## The Approach

Normal infrastructure operation has a geometry.
Attacks violate that geometry.

Sentinel learns the geometric manifold of normal plant operation.
It continuously measures deviation from that manifold.
High deviation equals anomaly equals alert.

No signatures. No cloud. No internet required. Fully air-gap capable.

## What It Detects

Zero-day attacks — no prior pattern needed
Slow-ramp manipulation — geometrically diverges over time
Coordinated multi-sensor attacks — collective geometry wrong
Sensor spoofing — identity mismatch from learned manifold
PLC project file tampering — process behavior changes geometrically

## Architecture

Three absolute constraints:
1. Zero cloud — all processing local
2. Zero signatures — detection is mathematical
3. Zero internet required — fully offline capable

Runs on Snapdragon SM8750 edge hardware.
Verified on 61 hardware thermal zones.

## Competitive Position

Capability          | Signature IDS | Threshold | Sentinel
Zero-day detection  | No            | No        | Yes
Cloud-free          | No            | Yes       | Yes
Evasion resistant   | No            | No        | Yes
Adaptive baseline   | No            | No        | Yes
Air-gap capable     | No            | Yes       | Yes

## Status

Operational on edge hardware.
SWaT/WADI dataset validation in progress.
Pilot deployments available under NDA.

## Contact

Chad Edward Holland
c.holland.arch@proton.me
github.com/holland202/sovereign-evolution

Full technical specifications under NDA only.
