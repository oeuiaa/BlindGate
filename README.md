# BlindGate: Privacy-Preserving DPI Gateway

BlindGate is a gateway-based architecture for performing **Deep Packet Inspection (DPI) on encrypted traffic** while preserving user privacy.

It adapts concepts from BlindBox and introduces a **client-transparent deployment model**, eliminating the need for endpoint modifications.

<em>Based on research paper:  BlindGatel A Gateway Architecture for Practical Privacy-Preserving Deep Packet Inspection on Encrypted Traffic</em>

---

## Overview

Traditional DPI becomes ineffective with TLS encryption. Existing solutions:

- Break privacy (MITM proxies)
- Require endpoint modification (BlindBox)

BlindGate solves this by:

- Performing **tokenization + encryption at a trusted gateway**
- Sending only **encrypted tokens** to an **untrusted IDS**
- Ensuring **plaintext never leaves the gateway**

---

## Architecture

Client → BlindGate (Trusted Gateway) → IDS (Untrusted)

### Key Idea

- Gateway (Trusted):
  - Intercepts traffic
  - Tokenizes payload
  - Encrypts tokens (HMAC-SHA256)
  - Sends encrypted tokens to IDS

- IDS (Untrusted):
  - Receives encrypted tokens
  - Matches against encrypted rule sets
  - Generates alerts

IDS never sees plaintext or keys.

---

## Core Concepts

### 1. Tokenization
- Sliding window (n-gram)
- Converts payload into substrings

### 2. Deterministic Encryption
- Algorithm: HMAC-SHA256
- Enables **equality matching without decryption**

### 3. Trust Model
- Gateway = Trusted
- IDS = Untrusted

---

## Project Structure
```
BLINDGATE/
│
├── blindgate_proxy.py          # HTTP interception + tokenization
├── blindgate_crypto.py         # Encryption logic (HMAC)
├── encrypted_rule_builder.py   # Rule preprocessing
├── blindgate_rule_server.py    # Rule distribution
├── rules.txt                   # Plaintext rules
├── run.sh                      # Orchestration script
│
├── proxy-logs/                 # Gateway logs
└── rules-logs/                 # IDS logs
```
```
IDS/
│
└── blindgate_ids.py            # Custom IDS engine
```
---

## How It Works

### 1. Rule Preparation (Offline)
```bash
python encrypted_rule_builder.py
```
Converts plaintext rules → encrypted tokens

### 2. Start System
```bash
./run.sh
```

### 3. Traffic Flow
```
	1.	Client sends HTTP request
	2.	Gateway intercepts traffic
	3.	Payload is:
		•	Tokenized
		•	Encrypted
	4.	Encrypted tokens → IDS
	5.	IDS performs matching → Alert
```
