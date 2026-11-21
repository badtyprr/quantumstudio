# qBraid reference discovery

The official documentation sitemap lists 106 pages in the SDK, PyQASM, QIR, Algorithms, Core, CLI and API Reference sections. Each page was retrieved, checked as Markdown and hashed. The page registry records all 907 fenced examples by language, position and digest. Stable QR identifiers bind syntax tasks to the page address. The public REST API description lists 27 method/path combinations. Each has a separate entry for its request-body and response metadata. [Documentation index](https://docs.qbraid.com/llms.txt) · [Sitemap](https://docs.qbraid.com/sitemap.xml) · [REST API description](https://docs.qbraid.com/openapi-v2.json)

| Reference area | Guide pages | Additional syntax inventory |
| --- | ---: | --- |
| SDK | 39 | 484 published Python objects |
| PyQASM | 6 | 23 published Python objects |
| QIR | 6 | 33 Python source modules and 48 top-level public definitions |
| Algorithms | 3 | 93 published Python objects |
| Core | 1 | 156 published Python objects |
| CLI | 22 | Per-page examples and source hashes |
| Runtime and REST API reference | 29 | 27 endpoint method/path pairs |

qbraid-reference-syntax.json contains the page and REST registries. qbraid-reference-symbols.json preserves each of the four Sphinx inventory digests and its object names, roles and documentation locations. Its QIR entries identify immutable Git blobs and line numbers of top-level definitions. The Sphinx manuals cover documented objects. QIR source definitions are a supplementary index and can include implementation functions.

Syntax acceptance requires checking the recorded constructs and examples in the applicable local importer or SDK. Provider results, authentication, authorization, submissions and hardware behavior each require independent execution evidence. Retrieving the public documentation and API schema involved no account access or job submissions. This inventory closes the dated reference-discovery task. Implementation, hosted provider and release acceptance remain open.
