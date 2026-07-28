#!/usr/bin/env python3
"""Extract OpenCollective transaction fields as NUL-separated records.

bash `read -r ... <<< "$tsv_line"` silently collapses consecutive empty fields
when IFS is a whitespace character (tab included), shifting every subsequent
field left by one. This breaks transactions with no visible email (anonymous
OC backers, child-project contributions). NUL cannot appear inside a JSON
string, so it is a safe field/record separator for bash `readarray -d ''`.

Usage: tx_fields.py <credit.jsonl>   (one JSON transaction object per line)

Emits, per transaction, 6 NUL-terminated fields in order:
  slug, email, amount, created_at, tier_slug, to_project_slug
"""
import sys
import json


def field(value):
    return "" if value is None else str(value)


def main():
    path = sys.argv[1]
    out = sys.stdout.buffer
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                tx = json.loads(line)
            except json.JSONDecodeError as e:
                # Ne jamais planter sur une ligne malformee : ca tronquerait
                # silencieusement toutes les transactions suivantes du fichier
                # (readarray recevrait un ensemble partiel sans que rien ne le signale,
                # cf. audit). On saute la ligne fautive et on continue les suivantes.
                print(f"tx_fields.py: ligne {lineno} ignoree (JSON invalide: {e})",
                      file=sys.stderr)
                continue
            from_account = tx.get("fromAccount") or {}
            emails = from_account.get("emails") or []
            order = tx.get("order") or {}
            tier = order.get("tier") or {}
            to_account = tx.get("toAccount") or {}
            amount = tx.get("amount") or {}
            amount_value = amount.get("value")
            values = (
                field(from_account.get("slug")),
                field(emails[0] if emails else None),
                field(amount_value if amount_value is not None else 0),
                field(tx.get("createdAt")),
                field(tier.get("slug")),
                field(to_account.get("slug")),
            )
            for v in values:
                out.write(v.encode("utf-8"))
                out.write(b"\0")


if __name__ == "__main__":
    main()
