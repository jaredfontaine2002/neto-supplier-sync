# Notes

## Why Safe Inbound Mode came before everything else

A supplier dispatch is NOT a customer dispatch. Getting that wrong means
emailing a customer that their order has shipped when it hasn't — only a
part has shipped to the shop. That rule was written first. The features
came second.

## The review queue is deliberate

Low-confidence matches go to a human review queue on purpose. A wrong
auto-match is worse than a slow manual one — the note would sit on the
wrong order and the real one would never get answered. If the tool isn't
sure, it waits for a person.

## Synthetic data only

All data in this public version is synthetic. Real supplier emails are
other people's business data — prices, accounts, order volumes — and
don't belong on GitHub. The public repo runs on invented distributors
and orders; the private version is the one that ever saw a real inbox.
