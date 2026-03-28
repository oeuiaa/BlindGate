from blindgate_crypto import tokenize, dpi_enc, normalize_payload

def build_rule(rule_text: str, window_size: int = 7):
	"""
	Takes a plaintext rule keyword and converts it to encrypted tokens,
	using the same normalization and tokenization as live traffic.
	"""
	# Normalize same way as payloads (lowercase, etc.)
	rule_bytes = normalize_payload(rule_text.encode())
	tokens = tokenize(rule_bytes, window_size)
	enc_tokens = [dpi_enc(t) for t in tokens]
	return enc_tokens

def load_rules_from_file(path: str = "rules.txt"):
	"""
	Load plaintext rules from a file. Ignores empty lines and comments (#).
	"""
	rules = []
	try:
		with open(path, "r") as f:
			for line in f:
				line = line.strip()
				if not line or line.startswith("#"):
					continue
				rules.append(line)
	except FileNotFoundError:
		print(f"[RuleBuilder] ERROR - Rules file '{path}' not found. No rules loaded.")
	return rules

if __name__ == "__main__":
	rules = load_rules_from_file()
	print(f"[RuleBuilder] Loaded {len(rules)} rules")
	for r in rules:
		toks = build_rule(r)
		print(f"Rule '{r}' -> {len(toks)} encrypted tokens")
