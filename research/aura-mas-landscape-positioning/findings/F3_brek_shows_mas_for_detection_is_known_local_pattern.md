---
name: F3_brek_shows_mas_for_detection_is_known_local_pattern
---
# F3 — A second local thesis (BREK 2019) already used "multi-agent systems for detection" framing, but for network/cyber intrusion, not physical surveillance

**Claim**: BREK Bouthaina's 2019 Master's thesis (Univ. Larbi Tébessa, outside Documents/, found in parent folder) implements four JADE agents, each wrapping a different pre-trained classifier (Naive Bayes, Decision Tree, RIPPER, Neural Net) over NSL-KDD network traffic data, coordinating via a confidence threshold that triggers ACL broadcast and JADE agent mobility. This is tabular/network data, zero computer vision.

**Evidence**: sources/08_brek-bouthaina-mas-intrusion-detection.md.

**Implication**: "Multi-agent systems + [X] detection" is an established, examinable thesis pattern at Algerian institutions — a jury may be primed to ask how a video-surveillance MAS differs architecturally from this kind of shallow "wrap a classifier per agent, coordinate via a threshold" pattern. The proposed AURA-MAS-style direction should explicitly differentiate its coordination mechanism (auction/contract-net with task allocation) from BREK's minimal threshold-broadcast-mobility scheme, which the source itself flags as never isolating the mobile-agent architecture's contribution from the classifiers' raw accuracy.

**Confidence**: High (full 63-page thesis read across 3 chunks).
