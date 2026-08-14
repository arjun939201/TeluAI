# v13 fixes

## Melimi leakage

The output firewall now has a small explicit leakage list for user-confirmed
problematic forms. It does not classify every unregistered Telugu word as a
loan. Current explicit repairs include:

- విశిష్ట → వేఱైన
- ఆసక్తికరం → హాళికాను
- ఆసక్తికరమైన → హాళికాను
- ఆసక్తికరంగా → హాళికానుగా

The authoritative corpus and registered mappings remain the main source.

## Groq one-message rate-limit failures

The previous prompt duplicated the full Melimi constitution and turn evidence,
which made even short requests unnecessarily expensive. v13 uses a compact
always-on contract, smaller retrieved context, a smaller response budget, and
`llama-3.1-8b-instant` as the free-tier-safe default in Render configuration.

A high-confidence `మేలిమి తెలుగు అంటే ఏమిటి?` FAQ is answered locally from the
language contract and does not consume Groq quota.

For short provider-supplied 429 reset windows (20 seconds or less), the backend
performs one bounded retry after the reset. Longer or quota-wide failures are
returned as a clear wait message rather than creating a retry loop.
