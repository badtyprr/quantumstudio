# IBM026 slides visual inventory plan

Input: ../ibm026-slide-acquisition-20261105/slides.pdf, SHA256 a79cc94cc28ebf9efd214364ffb616796fab520abe7a22a9f920659b40ff95ab, 474120bytes,41pages. Existing extracted page inventory is read-only. Exact source link and acquisition receipts remain in the preceding acquisition packet.

Reservation: do not render while IBM027 exclusive NATIVE slot is active. Wait for root slot-released message; no extra permission needed afterward.

After release, use bundled Poppler pdftoppm at150dpi PNG, pages1–41, one serialized rendering command,300-second limit, no network or source edits. Record renderer executable SHA256/version, exact argv, input before/after hashes, output sizes/SHA256/dimensions and timing/logs. Preserve initial output if rendering fails; report incomplete inventory rather than silently retrying.

Directly inspect all41 PNGs in manageable groups with page numbers retained. Reconcile visible headings, equations, circuit blocks/wires/labels and extraction ambiguities against the retained page text. Record one disposition per page, including clipping/readability and any unresolved label/order ambiguity. Page captions and topic mapping are descriptive only: do not assert formula truth, circuit equivalence, mathematical acceptance, original source-row completion, native/SDK/GUI/video or whole-lesson acceptance.

Expected topics from extraction: title1; spectral theorem2–3; phase-estimation problem4–5; kickback6–9; iteration10; two controls11–14; two-qubit phase-estimation15–16; QFT17–20; QFT circuits21–22; phase-estimation procedure23–28; order-finding29–32; eigenvectors33–37; implementation38–40; factoring41. Visual inspection may refine this map and must flag material extraction ambiguity.

Deliverables: render-manifest.json; pages/page-001.png through page-041.png; visual-inventory.json; REPORT.md. Supporting renderer script/log permitted. All evidence stays outside shared checkout and disposable clones.
