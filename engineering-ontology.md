## Global Software Engineering Standards Ontology

**Version:** 3.0
**Type:** Canonical Engineering Knowledge Graph
**License:** Open Reference
**Scope:** All major domains of modern software engineering

---

## 1. Ontology Rules

### 1.1 Loading Strategy

When used by an AI system:

- Load **only relevant domains** based on:
  - Language
  - Runtime
  - Deployment model

- Always include:
  - `security`
  - `internet_protocols`
  - `software_quality`

### 1.2 Priority Order

When multiple standards apply:

1. **Formal Standards (ISO, RFC, IEEE)**
2. **Living Standards (WHATWG, W3C)**
3. **Foundation Specs (CNCF, OpenAPI, etc.)**
4. **Industry De facto standards**

---

## 2. Entity Model

### 2.1 Standard Entity

```yaml
standard:
  id: unique_identifier
  name: string
  authority: reference_to_organization
  type: [formal | living | de_facto]
  domain: reference_to_domain
  version: optional
  status: [active | deprecated | draft]
  reference: url
  dependencies: []
  supersedes: optional
```

---

### 2.2 Organization Entity

```yaml
organization:
  id: string
  name: string
  category: [standards_body | foundation | consortium | government | nonprofit]
  authority_level: [global | regional | industry]
  url: string
```

---

## 3. Organization Registry (Normalized)

### 3.1 Formal Standards Bodies

```yaml
iso:
  name: International Organization for Standardization
  category: standards_body
  authority_level: global
  url: https://www.iso.org/

ieee:
  name: Institute of Electrical and Electronics Engineers
  category: standards_body
  authority_level: global
  url: https://standards.ieee.org/

ietf:
  name: Internet Engineering Task Force
  category: standards_body
  authority_level: global
  url: https://www.rfc-editor.org/

itu:
  name: International Telecommunication Union
  category: standards_body
  authority_level: global
  url: https://www.itu.int/

ecma:
  name: Ecma International
  category: standards_body
  authority_level: global
  url: https://www.ecma-international.org/

iana:
  name: Internet Assigned Numbers Authority
  category: standards_body
  authority_level: global
  url: https://www.iana.org/
```

---

### 3.2 Web Standards Bodies

```yaml
w3c:
  name: World Wide Web Consortium
  category: standards_body
  authority_level: global
  url: https://www.w3.org/

whatwg:
  name: Web Hypertext Application Technology Working Group
  category: consortium
  authority_level: global
  url: https://whatwg.org/

khronos:
  name: Khronos Group
  category: consortium
  authority_level: industry
  url: https://www.khronos.org/
```

---

### 3.3 Security & Government

```yaml
nist:
  name: National Institute of Standards and Technology
  category: government
  authority_level: global
  url: https://csrc.nist.gov/

mitre:
  name: MITRE Corporation
  category: nonprofit
  authority_level: global
  url: https://www.mitre.org/

owasp:
  name: Open Web Application Security Project
  category: nonprofit
  authority_level: global
  url: https://owasp.org/

enisa:
  name: European Union Agency for Cybersecurity
  category: government
  authority_level: regional
  url: https://www.enisa.europa.eu/
```

---

### 3.4 Open Source Foundations

```yaml
cncf:
  name: Cloud Native Computing Foundation
  category: foundation
  authority_level: industry
  url: https://www.cncf.io/

openssf:
  name: Open Source Security Foundation
  category: foundation
  authority_level: industry
  url: https://openssf.org/

linux_foundation:
  name: Linux Foundation
  category: foundation
  authority_level: industry
  url: https://www.linuxfoundation.org/

apache:
  name: Apache Software Foundation
  category: foundation
  authority_level: industry
  url: https://www.apache.org/

unicode_consortium:
  name: Unicode Consortium
  category: nonprofit
  authority_level: global
  url: https://home.unicode.org/
```

---

### 3.5 API & Identity Bodies

```yaml
openapi:
  name: OpenAPI Initiative
  category: consortium
  authority_level: industry
  url: https://www.openapis.org/

graphql_foundation:
  name: GraphQL Foundation
  category: foundation
  authority_level: industry
  url: https://graphql.org/

openid:
  name: OpenID Foundation
  category: foundation
  authority_level: industry
  url: https://openid.net/

oauth_wg:
  name: OAuth Working Group (IETF)
  category: standards_body
  authority_level: global
  url: https://datatracker.ietf.org/wg/oauth/about/
```

---

## 4. Domain Registry

```yaml
domains:
  foundation:
    - programming_languages
    - internet_protocols
    - web_platform

  engineering:
    - architecture
    - design_patterns
    - data_storage
    - api_design
    - distributed_systems

  infrastructure:
    - devops
    - cloud_native
    - containers
    - networking

  quality:
    - testing
    - software_quality
    - reliability

  security:
    - secure_sdlc
    - cryptography
    - identity_access
    - supply_chain

  observability:
    - logging
    - metrics
    - tracing
    - telemetry

  human_factors:
    - accessibility
    - ux
    - internationalization

  data_and_ai:
    - ml_lifecycle
    - model_governance
    - data_governance

  governance:
    - legal_frameworks
    - risk_management
    - audit
    - documentation
```

---

## 5. Cross-Domain Relationships

```yaml
relationships:
  - source: security
    relation: applies_to
    target: all_domains

  - source: observability
    relation: depends_on
    target: distributed_systems

  - source: api_design
    relation: depends_on
    target: internet_protocols

  - source: cloud_native
    relation: depends_on
    target: containers

  - source: accessibility
    relation: applies_to
    target: web_platform

  - source: ai_ml
    relation: depends_on
    target: data_governance

  - source: distributed_systems
    relation: depends_on
    target: networking

  - source: supply_chain
    relation: applies_to
    target: devops

  - source: identity_access
    relation: applies_to
    target: api_design

  - source: testing
    relation: applies_to
    target: all_domains
```

---

## 6. Programming Languages & Runtime Ecosystems

```yaml
programming_languages:
  classification:
    paradigms:
      - imperative
      - object_oriented
      - functional
      - declarative
      - logic
      - concurrent
      - dataflow

    runtime_models:
      - compiled
      - interpreted
      - bytecode_vm
      - jit
      - aot
      - hybrid

    memory_models:
      - manual
      - garbage_collected
      - reference_counted
      - ownership_based
```

---

### 6.1 ECMAScript Ecosystem

```yaml
javascript:
  standard: ECMA-262
  authority: ecma
  runtime: [jit, interpreted]
  environments: [browser, nodejs, deno, bun]
  memory_model: garbage_collected
  concurrency: [event_loop, async_await, web_workers]
  reference: https://tc39.es/ecma262/

javascript_i18n:
  standard: ECMA-402
  authority: ecma
  reference: https://tc39.es/ecma402/

typescript:
  type: superset
  compiles_to: javascript
  authority: microsoft
  reference: https://www.typescriptlang.org/docs/
```

---

### 6.2 JVM Ecosystem

```yaml
java:
  standard: Java Language Specification
  authority: oracle_openjdk
  runtime: bytecode_vm
  vm: jvm
  memory_model: garbage_collected
  concurrency: threads_plus_jmm
  reference: https://docs.oracle.com/javase/specs/

kotlin:
  authority: jetbrains
  runtime: bytecode_vm
  targets: [jvm, js, native]
  reference: https://kotlinlang.org/spec/

scala:
  authority: epfl_lightbend
  paradigm: [functional, oop]
  runtime: jvm
  reference: https://scala-lang.org/

groovy:
  authority: apache
  runtime: jvm
  reference: https://groovy-lang.org/

clojure:
  authority: clojure_core
  paradigm: functional
  runtime: jvm
  reference: https://clojure.org/
```

---

### 6.3 .NET Ecosystem

```yaml
csharp:
  standard: ECMA-334
  authority: ecma
  runtime: clr
  memory_model: garbage_collected
  reference: https://ecma-international.org/publications-and-standards/standards/ecma-334/

fsharp:
  authority: microsoft
  paradigm: functional
  runtime: clr
  reference: https://fsharp.org/

vb_net:
  authority: microsoft
  runtime: clr
  reference: https://learn.microsoft.com/en-us/dotnet/visual-basic/
```

---

### 6.4 Systems Programming Languages

```yaml
c:
  standard: ISO/IEC 9899
  authority: iso
  memory_model: manual
  runtime: compiled
  reference: https://www.iso.org/standard/74528.html

cpp:
  standard: ISO/IEC 14882
  authority: iso
  memory_model: manual
  runtime: compiled
  reference: https://www.iso.org/standard/79358.html

rust:
  authority: rust_project
  memory_model: ownership_based
  runtime: compiled
  safety: memory_safe
  reference: https://doc.rust-lang.org/reference/

zig:
  authority: zig_project
  memory_model: manual
  runtime: compiled
  reference: https://ziglang.org/documentation/master/

swift:
  authority: apple
  memory_model: reference_counted
  runtime: compiled
  reference: https://docs.swift.org/swift-book/

d:
  authority: d_lang_foundation
  memory_model: garbage_collected
  runtime: compiled
  reference: https://dlang.org/spec/spec.html
```

---

### 6.5 Functional Languages

```yaml
haskell:
  authority: haskell_committee
  paradigm: pure_functional
  runtime: compiled
  reference: https://www.haskell.org/

ocaml:
  authority: inria
  paradigm: functional
  runtime: compiled
  reference: https://ocaml.org/

elixir:
  authority: elixir_core_team
  runtime: beam_vm
  concurrency: actor_model
  reference: https://elixir-lang.org/

erlang:
  authority: ericsson
  runtime: beam_vm
  concurrency: actor_model
  reference: https://www.erlang.org/

purescript:
  authority: purescript_contributors
  paradigm: pure_functional
  compiles_to: javascript
  reference: https://www.purescript.org/
```

---

### 6.6 Scripting & General Purpose

```yaml
python:
  authority: python_software_foundation
  runtime: interpreted
  memory_model: garbage_collected
  reference: https://docs.python.org/3/reference/

ruby:
  authority: ruby_core_team
  runtime: interpreted
  reference: https://www.ruby-lang.org/

php:
  authority: php_group
  runtime: interpreted
  reference: https://www.php.net/docs.php

lua:
  authority: lua_org
  runtime: embedded
  reference: https://www.lua.org/manual/

perl:
  authority: perl_foundation
  runtime: interpreted
  reference: https://perldoc.perl.org/
```

---

### 6.7 Data & Query Languages

```yaml
sql:
  standard: ISO/IEC 9075
  authority: iso
  reference: https://www.iso.org/standard/63555.html

graphql:
  authority: graphql_foundation
  reference: https://spec.graphql.org/

sparql:
  authority: w3c
  reference: https://www.w3.org/TR/sparql11-query/

r:
  authority: r_core_team
  paradigm: statistical_computing
  reference: https://cran.r-project.org/doc/manuals/r-release/R-lang.html

datalog:
  type: logic_query_language
  used_in: [datomic, souffle, differential_dataflow]
```

---

### 6.8 Web & Markup Languages

```yaml
html:
  authority: whatwg
  reference: https://html.spec.whatwg.org/

css:
  authority: w3c
  reference: https://www.w3.org/TR/css/

xml:
  standard: W3C XML 1.0
  authority: w3c
  reference: https://www.w3.org/TR/xml/

json:
  standard: RFC 8259 / ECMA-404
  authority: [ietf, ecma]
  reference: https://www.rfc-editor.org/rfc/rfc8259

yaml:
  authority: yaml_org
  reference: https://yaml.org/spec/

markdown:
  authority: commonmark
  reference: https://spec.commonmark.org/

toml:
  authority: toml_project
  reference: https://toml.io/en/v1.0.0
```

---

### 6.9 GPU & Parallel Computing

```yaml
cuda:
  authority: nvidia
  runtime: gpu
  reference: https://docs.nvidia.com/cuda/

opencl:
  authority: khronos
  reference: https://www.khronos.org/opencl/

openmp:
  authority: openmp_arb
  reference: https://www.openmp.org/specifications/

wgsl:
  name: WebGPU Shading Language
  authority: w3c
  reference: https://www.w3.org/TR/WGSL/

glsl:
  name: OpenGL Shading Language
  authority: khronos
  reference: https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.4.60.pdf

hlsl:
  name: High-Level Shading Language
  authority: microsoft
```

---

### 6.10 Embedded & Hardware Description

```yaml
verilog:
  standard: IEEE 1364
  authority: ieee

vhdl:
  standard: IEEE 1076
  authority: ieee

systemverilog:
  standard: IEEE 1800
  authority: ieee

assembly:
  type: architecture_specific
  architectures: [x86_64, aarch64, riscv, arm, mips]
```

---

### 6.11 Emerging & Modern Languages

```yaml
go:
  authority: google
  runtime: compiled
  concurrency: goroutines
  memory_model: garbage_collected
  reference: https://go.dev/ref/spec

dart:
  authority: google
  runtime: [jit, aot]
  reference: https://dart.dev/guides/language/spec

nim:
  authority: nim_team
  runtime: compiled
  reference: https://nim-lang.org/docs/manual.html

crystal:
  authority: crystal_team
  runtime: compiled
  memory_model: garbage_collected
  reference: https://crystal-lang.org/reference/

julia:
  authority: julia_project
  runtime: jit
  paradigm: scientific_computing
  reference: https://docs.julialang.org/en/v1/

gleam:
  authority: gleam_team
  runtime: beam_vm
  paradigm: functional
  reference: https://gleam.run/
```

---

### 6.12 Package Ecosystems

```yaml
package_managers:
  npm:
    language: javascript
    registry: https://registry.npmjs.org/

  pip:
    language: python
    registry: https://pypi.org/

  cargo:
    language: rust
    registry: https://crates.io/

  maven:
    language: java
    registry: https://search.maven.org/

  nuget:
    language: dotnet
    registry: https://www.nuget.org/

  go_modules:
    language: go
    registry: https://proxy.golang.org/

  gem:
    language: ruby
    registry: https://rubygems.org/

  composer:
    language: php
    registry: https://packagist.org/

  hex:
    language: [elixir, erlang]
    registry: https://hex.pm/
```

---

## 7. Web Platform Domain

```yaml
web_platform:
  description: >
    The web platform consists of all standards governing browsers,
    document models, rendering, networking, APIs, and execution environments.
  authorities: [whatwg, w3c, ietf, ecma]
```

---

### 7.1 Core Document & Parsing Standards

```yaml
documents:
  html:
    name: HTML Living Standard
    authority: whatwg
    type: living
    reference: https://html.spec.whatwg.org/
    defines:
      - document_structure
      - parsing_algorithm
      - forms
      - media_elements
      - scripting_integration

  dom:
    name: DOM Standard
    authority: whatwg
    type: living
    reference: https://dom.spec.whatwg.org/
    defines:
      - node_tree
      - mutation_algorithms
      - event_dispatch

  infra:
    name: Infra Standard
    authority: whatwg
    reference: https://infra.spec.whatwg.org/
    defines:
      - fundamental_algorithms
      - string_processing
      - lists_maps_sets

  encoding:
    name: Encoding Standard
    authority: whatwg
    reference: https://encoding.spec.whatwg.org/
```

---

### 7.2 Styling & Layout (CSS Ecosystem)

```yaml
css:
  core:
    authority: w3c
    reference: https://www.w3.org/TR/css/
  modules:
    css_syntax:
      reference: https://www.w3.org/TR/css-syntax-3/
    css_cascade:
      reference: https://www.w3.org/TR/css-cascade-5/
    css_box_model:
      reference: https://www.w3.org/TR/css-box-3/
    css_display:
      reference: https://www.w3.org/TR/css-display-3/
    css_flexbox:
      reference: https://www.w3.org/TR/css-flexbox-1/
    css_grid:
      reference: https://www.w3.org/TR/css-grid-2/
    css_positioning:
      reference: https://www.w3.org/TR/css-position-3/
    css_transforms:
      reference: https://www.w3.org/TR/css-transforms-1/
    css_transitions:
      reference: https://www.w3.org/TR/css-transitions-1/
    css_animations:
      reference: https://www.w3.org/TR/css-animations-1/
    css_variables:
      reference: https://www.w3.org/TR/css-variables-1/
    css_media_queries:
      reference: https://www.w3.org/TR/mediaqueries-5/
    css_containment:
      reference: https://www.w3.org/TR/css-contain-3/
    css_color:
      reference: https://www.w3.org/TR/css-color-4/
    css_fonts:
      reference: https://www.w3.org/TR/css-fonts-4/
```

---

### 7.3 Rendering & Graphics

```yaml
rendering:
  canvas:
    name: HTML Canvas 2D Context
    authority: whatwg
    reference: https://html.spec.whatwg.org/
  webgl:
    authority: khronos
    reference: https://registry.khronos.org/webgl/specs/latest/
  webgpu:
    authority: w3c
    reference: https://www.w3.org/TR/webgpu/
  svg:
    authority: w3c
    reference: https://www.w3.org/TR/SVG2/
  mathml:
    authority: w3c
    reference: https://www.w3.org/TR/mathml-core/
```

---

### 7.4 Networking & Data Fetching

```yaml
web_networking:
  fetch:
    authority: whatwg
    reference: https://fetch.spec.whatwg.org/
    defines: [request_lifecycle, response_handling, cors]
  xhr:
    name: XMLHttpRequest
    authority: whatwg
    reference: https://xhr.spec.whatwg.org/
  websockets:
    authority: whatwg
    reference: https://websockets.spec.whatwg.org/
  server_sent_events:
    authority: whatwg
    reference: https://html.spec.whatwg.org/
  cors:
    authority: whatwg
    defined_in: fetch
  url:
    authority: whatwg
    reference: https://url.spec.whatwg.org/
```

---

### 7.5 Storage & Persistence

```yaml
web_storage:
  local_session_storage:
    name: Web Storage
    authority: whatwg
    reference: https://html.spec.whatwg.org/
  indexeddb:
    authority: w3c
    reference: https://www.w3.org/TR/IndexedDB-3/
  cache_api:
    authority: w3c
    reference: https://www.w3.org/TR/service-workers/
  cookies:
    authority: ietf
    standard: RFC 6265
    reference: https://www.rfc-editor.org/rfc/rfc6265
  opfs:
    name: Origin Private File System
    authority: whatwg
    reference: https://fs.spec.whatwg.org/
```

---

### 7.6 Execution & Workers

```yaml
web_execution:
  javascript_engine:
    standard: ECMA-262
    authority: ecma
  event_loop:
    authority: whatwg
    defined_in: html
  web_workers:
    authority: w3c
    reference: https://www.w3.org/TR/workers/
  service_workers:
    authority: w3c
    reference: https://www.w3.org/TR/service-workers/
  worklets:
    authority: w3c
    reference: https://www.w3.org/TR/worklets-1/
  wasm:
    name: WebAssembly
    authority: w3c
    reference: https://webassembly.github.io/spec/core/
```

---

### 7.7 Media & Real-Time Communication

```yaml
web_media:
  html_media:
    authority: whatwg
    defined_in: html
  webrtc:
    authority: w3c
    reference: https://www.w3.org/TR/webrtc/
  mediastream:
    authority: w3c
    reference: https://www.w3.org/TR/mediacapture-streams/
  web_audio:
    authority: w3c
    reference: https://www.w3.org/TR/webaudio/
  media_source:
    authority: w3c
    reference: https://www.w3.org/TR/media-source-2/
```

---

### 7.8 Device & Hardware APIs

```yaml
device_apis:
  geolocation:
    authority: w3c
    reference: https://www.w3.org/TR/geolocation/
  device_orientation:
    authority: w3c
    reference: https://www.w3.org/TR/orientation-event/
  webusb:
    authority: w3c
    reference: https://wicg.github.io/webusb/
  webbluetooth:
    authority: w3c
    reference: https://webbluetoothcg.github.io/web-bluetooth/
  clipboard:
    authority: w3c
    reference: https://www.w3.org/TR/clipboard-apis/
  screen_wake_lock:
    authority: w3c
    reference: https://www.w3.org/TR/screen-wake-lock/
```

---

### 7.9 Security (Web-Specific)

```yaml
web_security:
  same_origin_policy:
    authority: whatwg
    defined_in: html
  content_security_policy:
    authority: w3c
    reference: https://www.w3.org/TR/CSP3/
  cors:
    authority: whatwg
    defined_in: fetch
  referrer_policy:
    authority: w3c
    reference: https://www.w3.org/TR/referrer-policy/
  webauthn:
    authority: w3c
    reference: https://www.w3.org/TR/webauthn-2/
  secure_contexts:
    authority: w3c
    reference: https://www.w3.org/TR/secure-contexts/
  permissions_policy:
    authority: w3c
    reference: https://www.w3.org/TR/permissions-policy-1/
  subresource_integrity:
    authority: w3c
    reference: https://www.w3.org/TR/SRI/
```

---

### 7.10 Performance & Scheduling

```yaml
web_performance:
  performance_api:
    authority: w3c
    reference: https://www.w3.org/TR/performance-timeline/
  navigation_timing:
    authority: w3c
    reference: https://www.w3.org/TR/navigation-timing-2/
  resource_timing:
    authority: w3c
    reference: https://www.w3.org/TR/resource-timing/
  long_tasks:
    authority: w3c
    reference: https://www.w3.org/TR/longtasks-1/
  request_idle_callback:
    authority: w3c
    reference: https://www.w3.org/TR/requestidlecallback/
  core_web_vitals:
    authority: google
    reference: https://web.dev/vitals/
```

---

### 7.11 Progressive Web Apps (PWA)

```yaml
pwa:
  manifest:
    authority: w3c
    reference: https://www.w3.org/TR/appmanifest/
  service_workers:
    authority: w3c
  offline_capabilities:
    depends_on: [cache_api, service_workers]
  push_notifications:
    authority: w3c
    reference: https://www.w3.org/TR/push-api/
```

---

### 7.12 Accessibility Integration

```yaml
web_accessibility_integration:
  aria:
    authority: w3c
    reference: https://www.w3.org/TR/wai-aria-1.2/
  html_accessibility:
    authority: whatwg
  aom:
    name: Accessibility Object Model
    authority: w3c
    status: draft
```

---

### 7.13 Packaging & Modules

```yaml
web_modules:
  es_modules:
    authority: ecma
    defined_in: ecma262
  import_maps:
    authority: w3c
    reference: https://wicg.github.io/import-maps/
  web_bundles:
    authority: w3c
    status: draft
```

---

### 7.14 Interoperability & Compatibility

```yaml
web_interop:
  web_platform_tests:
    authority: w3c
    reference: https://web-platform-tests.org/
  browser_compat_data:
    authority: mdn
    reference: https://github.com/mdn/browser-compat-data
  baseline:
    authority: webdx
    reference: https://web.dev/baseline/
```

---

## 8. Internet Protocols

```yaml
internet_protocols:
  description: >
    Standards governing communication over networks.
    Organized by OSI/TCP-IP layer.
  primary_authority: ietf
  layer_model: [physical, datalink, network, transport, session, presentation, application]
```

---

### 8.1 Network Layer

```yaml
network_layer:
  ipv4:
    standard: RFC 791
    authority: ietf
    reference: https://www.rfc-editor.org/rfc/rfc791

  ipv6:
    standard: RFC 8200
    authority: ietf
    reference: https://www.rfc-editor.org/rfc/rfc8200

  icmp:
    standard: RFC 792
    authority: ietf

  icmpv6:
    standard: RFC 4443
    authority: ietf

  bgp:
    name: Border Gateway Protocol
    standard: RFC 4271
    authority: ietf

  ospf:
    name: Open Shortest Path First
    standard: RFC 5340
    authority: ietf
```

---

### 8.2 Transport Layer

```yaml
transport_layer:
  tcp:
    standard: RFC 9293
    authority: ietf
    reference: https://www.rfc-editor.org/rfc/rfc9293
    features: [reliable, ordered, flow_control, congestion_control]

  udp:
    standard: RFC 768
    authority: ietf
    features: [connectionless, low_latency]

  quic:
    standard: RFC 9000
    authority: ietf
    reference: https://www.rfc-editor.org/rfc/rfc9000
    features: [multiplexed, encrypted, 0rtt]
    replaces: [tcp_tls]

  sctp:
    standard: RFC 4960
    authority: ietf
    features: [multi_streaming, multi_homing]
```

---

### 8.3 Application Layer — Web

```yaml
application_web:
  http_1_1:
    standard: RFC 9110 / RFC 9112
    authority: ietf
    reference: https://www.rfc-editor.org/rfc/rfc9110

  http_2:
    standard: RFC 9113
    authority: ietf
    reference: https://www.rfc-editor.org/rfc/rfc9113
    features: [multiplexing, header_compression, server_push]

  http_3:
    standard: RFC 9114
    authority: ietf
    reference: https://www.rfc-editor.org/rfc/rfc9114
    transport: quic

  websocket:
    standard: RFC 6455
    authority: ietf
    reference: https://www.rfc-editor.org/rfc/rfc6455

  webrtc_transport:
    relates_to: [RFC 8825, RFC 8826, RFC 8827]
    authority: ietf
```

---

### 8.4 Application Layer — Messaging

```yaml
application_messaging:
  smtp:
    standard: RFC 5321
    authority: ietf

  imap:
    standard: RFC 9051
    authority: ietf

  mqtt:
    standard: OASIS MQTT 5.0
    authority: oasis
    use_case: iot_messaging

  amqp:
    standard: OASIS AMQP 1.0
    authority: oasis
    use_case: enterprise_messaging

  nats:
    authority: nats_io
    type: de_facto
    use_case: cloud_native_messaging

  grpc:
    authority: cncf
    transport: http_2
    serialization: protobuf
    reference: https://grpc.io/docs/
```

---

### 8.5 Application Layer — Data & Directory

```yaml
application_data:
  dns:
    standard: RFC 1034 / RFC 1035
    authority: ietf
    extensions: [DNSSEC RFC 4033, DoT RFC 7858, DoH RFC 8484]

  ftp:
    standard: RFC 959
    authority: ietf
    status: legacy

  sftp:
    standard: draft-ietf-secsh-filexfer
    authority: ietf

  ntp:
    standard: RFC 5905
    authority: ietf

  ldap:
    standard: RFC 4511
    authority: ietf
```

---

### 8.6 Security Protocols

```yaml
security_protocols:
  tls:
    standard: RFC 8446
    name: TLS 1.3
    authority: ietf
    reference: https://www.rfc-editor.org/rfc/rfc8446
    deprecates: [tls_1_0, tls_1_1, ssl_3_0]

  dtls:
    standard: RFC 9147
    authority: ietf
    transport: udp

  ssh:
    standard: RFC 4251
    authority: ietf

  ipsec:
    standard: RFC 4301
    authority: ietf
    components: [IKEv2 RFC 7296, ESP RFC 4303, AH RFC 4302]

  wireguard:
    authority: wireguard_project
    type: de_facto
    reference: https://www.wireguard.com/papers/wireguard.pdf
```

---

### 8.7 Encoding & Serialization Formats

```yaml
encoding_formats:
  json:
    standard: RFC 8259 / ECMA-404
    authority: [ietf, ecma]

  cbor:
    standard: RFC 8949
    authority: ietf
    use_case: compact_binary_json

  protobuf:
    authority: google
    type: de_facto
    reference: https://protobuf.dev/

  messagepack:
    authority: msgpack_org
    type: de_facto

  avro:
    authority: apache
    use_case: data_streaming

  parquet:
    authority: apache
    use_case: columnar_storage

  xml:
    standard: W3C XML 1.0
    authority: w3c

  base64:
    standard: RFC 4648
    authority: ietf
```

---

## 9. Software Architecture

```yaml
software_architecture:
  description: >
    Structural organization of software systems.
    Standards from ISO/IEC/IEEE 42010 govern documentation and viewpoints.
  standard: ISO/IEC/IEEE 42010
  authority: [iso, ieee]
  reference: https://www.iso.org/standard/50508.html
```

---

### 9.1 Architectural Styles

```yaml
architectural_styles:
  monolithic:
    description: Single deployable unit
    trade_offs: [simple, hard_to_scale_independently]

  layered:
    description: Horizontal separation of concerns
    examples: [presentation, business_logic, data]

  microservices:
    description: Independently deployable services
    reference_model: [CNCF whitepaper]

  event_driven:
    description: Components communicate via events
    patterns: [event_sourcing, cqrs, saga]

  hexagonal:
    name: Ports & Adapters
    author: Alistair Cockburn
    enforces: dependency_inversion

  clean:
    name: Clean Architecture
    author: Robert C. Martin
    enforces: [dependency_rule, independence_of_frameworks]

  service_mesh:
    description: Infrastructure layer for service-to-service communication
    examples: [istio, linkerd, cilium]

  serverless:
    description: Function-as-a-Service execution model
    examples: [aws_lambda, cloudflare_workers, azure_functions]
```

---

### 9.2 Architectural Principles

```yaml
architectural_principles:
  solid:
    components:
      srp: Single Responsibility Principle
      ocp: Open/Closed Principle
      lsp: Liskov Substitution Principle
      isp: Interface Segregation Principle
      dip: Dependency Inversion Principle

  dry: Don't Repeat Yourself
  kiss: Keep It Simple, Stupid
  yagni: You Aren't Gonna Need It
  separation_of_concerns: Isolate distinct responsibilities
  law_of_demeter: Minimal knowledge principle
  composition_over_inheritance: Prefer composition
  fail_fast: Surface errors early
```

---

### 9.3 Architecture Documentation

```yaml
architecture_documentation:
  iso_42010:
    name: ISO/IEC/IEEE 42010 Systems and Software Architecture Description
    authority: [iso, ieee]

  arc42:
    type: de_facto_template
    reference: https://arc42.org/

  c4_model:
    type: de_facto
    levels: [context, containers, components, code]
    reference: https://c4model.com/

  adr:
    name: Architecture Decision Records
    type: practice
    reference: https://adr.github.io/
```

---

## 10. Design Patterns

```yaml
design_patterns:
  description: >
    Reusable solutions to recurring software design problems.
    Categorized per the Gang of Four taxonomy.
  reference: Design Patterns (GoF), Enterprise Integration Patterns (Hohpe & Woolf)
```

---

### 10.1 Creational Patterns

```yaml
creational:
  - singleton
  - factory_method
  - abstract_factory
  - builder
  - prototype
  - object_pool
```

---

### 10.2 Structural Patterns

```yaml
structural:
  - adapter
  - bridge
  - composite
  - decorator
  - facade
  - flyweight
  - proxy
```

---

### 10.3 Behavioral Patterns

```yaml
behavioral:
  - chain_of_responsibility
  - command
  - interpreter
  - iterator
  - mediator
  - memento
  - observer
  - state
  - strategy
  - template_method
  - visitor
```

---

### 10.4 Concurrency Patterns

```yaml
concurrency:
  - active_object
  - half_sync_half_async
  - reactor
  - proactor
  - thread_pool
  - monitor
  - read_write_lock
  - scheduler
```

---

### 10.5 Enterprise Integration Patterns

```yaml
enterprise_integration:
  messaging:
    - message_channel
    - message_router
    - message_translator
    - message_endpoint
    - pipes_and_filters
  routing:
    - content_based_router
    - message_filter
    - dynamic_router
    - recipient_list
    - splitter
    - aggregator
    - resequencer
  transformation:
    - message_translator
    - envelope_wrapper
    - content_enricher
    - content_filter
    - normalizer
  endpoints:
    - polling_consumer
    - event_driven_consumer
    - competing_consumers
    - transactional_client
  reference: Enterprise Integration Patterns (Hohpe & Woolf)
```

---

### 10.6 Cloud-Native Patterns

```yaml
cloud_native_patterns:
  resilience:
    - circuit_breaker
    - retry_with_backoff
    - bulkhead
    - timeout
    - fallback
    - rate_limiter
  data:
    - saga
    - cqrs
    - event_sourcing
    - outbox
    - two_phase_commit
  deployment:
    - sidecar
    - ambassador
    - adapter
    - blue_green
    - canary
    - feature_flag
    - strangler_fig
```

---

## 11. Data & Storage

```yaml
data_storage:
  description: >
    Standards and models governing data definition, storage, retrieval,
    and lifecycle management.
```

---

### 11.1 Relational Databases

```yaml
relational:
  sql_standard:
    standard: ISO/IEC 9075
    authority: iso
    versions: [SQL:1992, SQL:1999, SQL:2003, SQL:2011, SQL:2016, SQL:2023]

  acid:
    properties:
      atomicity: All-or-nothing transactions
      consistency: Constraints always satisfied
      isolation: Concurrent transactions non-interfering
      durability: Committed data persists

  normal_forms:
    - 1NF
    - 2NF
    - 3NF
    - BCNF
    - 4NF
    - 5NF
```

---

### 11.2 NoSQL & Non-Relational

```yaml
nosql:
  document:
    examples: [mongodb, couchdb, firestore]
    use_case: flexible_schema

  key_value:
    examples: [redis, memcached, dynamodb]
    use_case: [cache, session_store]

  column_family:
    examples: [cassandra, hbase]
    use_case: write_heavy_time_series

  graph:
    examples: [neo4j, tigergraph, amazon_neptune]
    standards: [RDF, SPARQL, Property_Graph, Gremlin]

  time_series:
    examples: [influxdb, timescaledb, prometheus]
    use_case: metrics_telemetry

  vector:
    examples: [pinecone, weaviate, qdrant, pgvector]
    use_case: semantic_search_and_ml
```

---

### 11.3 Distributed Data Principles

```yaml
distributed_data:
  cap_theorem:
    description: Consistency, Availability, Partition-tolerance — pick two
    author: Eric Brewer

  pacelc:
    description: Extension of CAP including latency trade-offs

  consistency_models:
    - linearizability
    - sequential_consistency
    - causal_consistency
    - eventual_consistency
    - read_your_writes

  replication_strategies:
    - single_leader
    - multi_leader
    - leaderless

  partitioning:
    - range_partitioning
    - hash_partitioning
    - consistent_hashing
```

---

### 11.4 Data Formats & Interchange

```yaml
data_formats:
  json: { standard: RFC 8259 }
  csv: { standard: RFC 4180 }
  parquet: { authority: apache, type: columnar }
  orc: { authority: apache, type: columnar }
  avro: { authority: apache, type: row_based_streaming }
  arrow: { authority: apache, type: in_memory_columnar }
  hdf5: { authority: hdf_group, type: hierarchical }
```

---

### 11.5 Data Governance

```yaml
data_governance:
  data_catalog:
    description: Metadata management and discovery
    examples: [apache_atlas, datahub, openmetadata]

  data_lineage:
    description: Tracking data origin and transformations
    standard: OpenLineage
    reference: https://openlineage.io/

  data_quality:
    dimensions: [accuracy, completeness, consistency, timeliness, validity, uniqueness]

  data_privacy:
    frameworks:
      gdpr:
        authority: european_union
        reference: https://gdpr.eu/
      ccpa:
        authority: california
      hipaa:
        authority: us_hhs
        applies_to: health_data
```

---

## 12. API Design

```yaml
api_design:
  description: >
    Standards governing the design, documentation, and lifecycle of APIs.
```

---

### 12.1 REST

```yaml
rest:
  originator: Roy Fielding (dissertation, 2000)
  constraints:
    - client_server
    - stateless
    - cacheable
    - uniform_interface
    - layered_system
    - code_on_demand

  maturity_model:
    reference: Richardson Maturity Model
    levels:
      0: POX (plain old XML) / RPC
      1: Resources
      2: HTTP verbs
      3: Hypermedia controls (HATEOAS)

  http_semantics:
    standard: RFC 9110
    authority: ietf

  status_codes:
    standard: RFC 9110
    informational: 1xx
    success: 2xx
    redirection: 3xx
    client_error: 4xx
    server_error: 5xx

  content_negotiation:
    standard: RFC 9110
    types: [Accept, Content-Type, Accept-Language]
```

---

### 12.2 OpenAPI Specification

```yaml
openapi:
  version: "3.1"
  authority: openapi_initiative
  reference: https://spec.openapis.org/oas/v3.1.0
  tooling: [swagger_ui, redoc, stoplight, spectral]
  extends: JSON Schema draft-07
```

---

### 12.3 GraphQL

```yaml
graphql:
  authority: graphql_foundation
  reference: https://spec.graphql.org/
  operations: [query, mutation, subscription]
  introspection: true
  transport: http_post
  tooling: [apollo, graphql_yoga, strawberry, async_graphql]
```

---

### 12.4 gRPC & Protobuf

```yaml
grpc:
  authority: cncf
  transport: http_2
  idl: protobuf
  streaming: [unary, server_streaming, client_streaming, bidirectional]
  reference: https://grpc.io/docs/

protobuf:
  authority: google
  version: proto3
  reference: https://protobuf.dev/
```

---

### 12.5 AsyncAPI

```yaml
asyncapi:
  authority: asyncapi_initiative
  version: "3.0"
  reference: https://www.asyncapi.com/docs/reference/specification/v3.0.0
  use_case: event_driven_and_async_apis
  protocols: [amqp, mqtt, kafka, websocket, nats]
```

---

### 12.6 API Security

```yaml
api_security:
  authentication:
    bearer_tokens:
      standard: RFC 6750
    api_keys: common_practice
    mutual_tls: RFC 8705

  authorization:
    oauth2:
      standard: RFC 6749 / RFC 6750
      authority: ietf
      flows: [authorization_code, client_credentials, device_flow]
    oidc:
      standard: OpenID Connect Core 1.0
      authority: openid
      reference: https://openid.net/specs/openid-connect-core-1_0.html

  rate_limiting: common_practice
  input_validation:
    cwe: CWE-20
    notes: Validate all inputs at API boundary

  api_security_top_10:
    authority: owasp
    reference: https://owasp.org/www-project-api-security/
```

---

### 12.7 Versioning Strategies

```yaml
api_versioning:
  url_path: /v1/resource
  query_parameter: ?version=1
  header: Accept-Version or custom header
  media_type: application/vnd.example.v1+json
  notes: URL path versioning most common in REST; header preferred for purists
```

---

## 13. Distributed Systems

```yaml
distributed_systems:
  description: >
    Principles and standards governing systems of independent components
    that communicate over a network.
```

---

### 13.1 Foundational Concepts

```yaml
distributed_foundations:
  fallacies_of_distributed_computing:
    author: Peter Deutsch / Sun Microsystems
    fallacies:
      - The network is reliable
      - Latency is zero
      - Bandwidth is infinite
      - The network is secure
      - Topology doesn't change
      - There is one administrator
      - Transport cost is zero
      - The network is homogeneous

  consensus:
    algorithms:
      paxos:
        reference: Lamport (1989)
      raft:
        reference: Ongaro & Ousterhout (2014)
        reference_url: https://raft.github.io/
      pbft:
        name: Practical Byzantine Fault Tolerance
        use_case: byzantine_fault_tolerant_systems
      zab:
        use_case: apache_zookeeper

  logical_clocks:
    lamport_clocks: total_ordering
    vector_clocks: causality_tracking
    hybrid_logical_clocks: combines physical + logical
```

---

### 13.2 Messaging & Event Streaming

```yaml
event_streaming:
  kafka:
    authority: apache
    type: distributed_log
    model: [publish_subscribe, log_compaction, consumer_groups]
    reference: https://kafka.apache.org/

  pulsar:
    authority: apache
    type: distributed_messaging_streaming
    features: [multi_tenancy, geo_replication, tiered_storage]

  event_sourcing:
    pattern: Store state changes as immutable events
    relates_to: [cqrs, outbox_pattern]

  cloudevents:
    authority: cncf
    reference: https://cloudevents.io/
    purpose: Standardized event envelope format
```

---

### 13.3 Service Discovery & Coordination

```yaml
service_discovery:
  client_side: [eureka, consul]
  server_side: [kubernetes_service, aws_elb]

  coordination:
    zookeeper:
      authority: apache
      use_case: [leader_election, config_store, distributed_locking]
    etcd:
      authority: cncf
      use_case: [kubernetes_store, config_store, leader_election]

  health_checking:
    patterns: [HTTP_health_endpoint, TCP_probe, gRPC_health_check]
    grpc_health_check:
      standard: grpc.health.v1
      reference: https://github.com/grpc/grpc/blob/master/doc/health-checking.md
```

---

### 13.4 Distributed Transactions

```yaml
distributed_transactions:
  two_phase_commit:
    abbreviation: 2PC
    trade_off: blocking_on_coordinator_failure

  saga:
    variants: [choreography, orchestration]
    compensating_transactions: required

  outbox_pattern:
    description: Write event to DB and message bus atomically
    solves: dual_write_problem
```

---

## 14. DevOps & CI/CD

```yaml
devops:
  description: >
    Cultural and technical practices for integrating development and operations.
    Standards from DORA metrics, CNCF, and ISO/IEC 20000.
```

---

### 14.1 Core Principles

```yaml
devops_principles:
  dora_metrics:
    authority: DORA (Google)
    reference: https://dora.dev/
    metrics:
      deployment_frequency: How often code is deployed to production
      lead_time_for_changes: Time from commit to production
      change_failure_rate: Percentage of changes causing incidents
      time_to_restore: Time to restore service after incident

  three_ways:
    source: The Phoenix Project / DevOps Handbook
    principles:
      - flow_and_systems_thinking
      - amplify_feedback_loops
      - culture_of_experimentation

  shift_left:
    description: Move testing, security, compliance earlier in the lifecycle
    applies_to: [testing, security, compliance]
```

---

### 14.2 CI/CD Pipeline Standards

```yaml
cicd_pipeline:
  stages:
    - source_control
    - build
    - unit_test
    - integration_test
    - security_scan
    - artifact_publish
    - deploy_staging
    - acceptance_test
    - deploy_production
    - monitoring

  artifact_standards:
    sbom: [SPDX, CycloneDX]
    signatures: [Sigstore / Cosign]
    registry: [OCI Distribution Spec]

  pipeline_as_code:
    examples: [GitHub Actions, GitLab CI, Jenkins Pipeline, Tekton, Argo Workflows]

  slsa_levels:
    authority: openssf
    reference: https://slsa.dev/spec/
    levels:
      1: Provenance generated
      2: Hosted build platform
      3: Hardened builds
      4: Hermetic and reproducible
```

---

### 14.3 Infrastructure as Code

```yaml
infrastructure_as_code:
  declarative:
    terraform:
      authority: hashicorp
      language: HCL
      reference: https://developer.hashicorp.com/terraform
    pulumi:
      authority: pulumi_corp
      languages: [typescript, python, go, csharp, java]
    opentofu:
      authority: linux_foundation
      fork_of: terraform

  configuration_management:
    ansible:
      authority: redhat
      model: agentless_push
    chef:
      model: agent_pull
    puppet:
      model: agent_pull

  templating:
    helm:
      authority: cncf
      use_case: kubernetes_packaging
    kustomize:
      authority: kubernetes_sigs
      model: overlay_patches
```

---

### 14.4 GitOps

```yaml
gitops:
  principles:
    authority: cncf_opengitops
    reference: https://opengitops.dev/
    four_principles:
      - declarative
      - versioned_and_immutable
      - pulled_automatically
      - continuously_reconciled

  tools:
    argocd:
      authority: cncf
    flux:
      authority: cncf
```

---

## 15. Cloud-Native & Containers

```yaml
cloud_native:
  description: >
    Practices and technologies for building and running scalable
    applications in modern, dynamic environments.
  authority: cncf
  reference: https://www.cncf.io/
```

---

### 15.1 Container Standards

```yaml
container_standards:
  oci_image:
    name: OCI Image Format Specification
    authority: oci
    reference: https://github.com/opencontainers/image-spec

  oci_runtime:
    name: OCI Runtime Specification
    authority: oci
    reference: https://github.com/opencontainers/runtime-spec
    implementations: [runc, crun, youki]

  oci_distribution:
    name: OCI Distribution Specification
    authority: oci
    reference: https://github.com/opencontainers/distribution-spec
    implementations: [docker_registry, harbor, ghcr, ecr, gcr]
```

---

### 15.2 Container Runtimes & Engines

```yaml
container_runtimes:
  high_level:
    docker:
      authority: docker_inc
      type: de_facto
    containerd:
      authority: cncf
    podman:
      authority: redhat

  low_level:
    runc:
      authority: oci
    crun:
      authority: redhat
    gvisor:
      authority: google
      sandboxing: user_space_kernel

  wasm_runtimes:
    wasmtime:
      authority: bytecode_alliance
    wasmer:
      authority: wasmer_inc
    wasm_edge:
      authority: cncf
```

---

### 15.3 Kubernetes

```yaml
kubernetes:
  authority: cncf
  reference: https://kubernetes.io/
  api_version_scheme: [alpha, beta, stable]

  core_objects:
    workloads: [Pod, Deployment, StatefulSet, DaemonSet, Job, CronJob]
    networking: [Service, Ingress, NetworkPolicy, EndpointSlice]
    config: [ConfigMap, Secret, ServiceAccount]
    storage: [PersistentVolume, PersistentVolumeClaim, StorageClass]
    rbac: [Role, ClusterRole, RoleBinding, ClusterRoleBinding]

  extension_points:
    - CRD (Custom Resource Definitions)
    - Admission Webhooks
    - CNI (Container Network Interface)
    - CSI (Container Storage Interface)
    - CRI (Container Runtime Interface)

  cni:
    standard: CNI Spec
    authority: cncf
    implementations: [calico, cilium, flannel, weave]

  service_mesh:
    implementations: [istio, linkerd, cilium_mesh]
```

---

### 15.4 Cloud Providers

```yaml
cloud_providers:
  aws:
    authority: amazon
    certifications: [ISO 27001, SOC 2, FedRAMP]

  gcp:
    authority: google
    certifications: [ISO 27001, SOC 2, FedRAMP]

  azure:
    authority: microsoft
    certifications: [ISO 27001, SOC 2, FedRAMP]

  cloud_interop:
    multi_cloud_standard: TOSCA (OASIS)
    portability: [OpenAPI, Kubernetes, OCI, Terraform]
```

---

### 15.5 Serverless

```yaml
serverless:
  models:
    faas: Function-as-a-Service
    caas: Container-as-a-Service
    baas: Backend-as-a-Service

  knative:
    authority: cncf
    use_case: kubernetes_serverless

  cloudevents:
    authority: cncf
    use_case: standard_event_envelope

  wasm_edge_compute:
    use_case: sub_millisecond_cold_start
    runtimes: [wasmtime, wasm_edge]
```

---

## 16. Networking

```yaml
networking:
  description: >
    Deep coverage of network architecture, protocols, and operations.
    Complements the internet protocols section with infrastructure focus.
```

---

### 16.1 Network Architecture Models

```yaml
network_models:
  osi_model:
    layers:
      1: Physical
      2: Data Link
      3: Network
      4: Transport
      5: Session
      6: Presentation
      7: Application

  tcp_ip_model:
    layers:
      1: Network Access (Link)
      2: Internet
      3: Transport
      4: Application
```

---

### 16.2 Load Balancing

```yaml
load_balancing:
  algorithms:
    - round_robin
    - weighted_round_robin
    - least_connections
    - ip_hash
    - consistent_hashing
    - resource_based

  layers:
    l4: Transport-layer (TCP/UDP)
    l7: Application-layer (HTTP/gRPC)

  implementations: [nginx, haproxy, envoy, traefik, aws_alb]
```

---

### 16.3 CDN & Edge

```yaml
cdn_edge:
  cdn:
    description: Content Delivery Network — geographically distributed cache
    examples: [cloudflare, fastly, aws_cloudfront, akamai]

  edge_compute:
    description: Compute at CDN PoPs, near user
    examples: [cloudflare_workers, fastly_compute, vercel_edge]

  anycast: IP routing technique used by DNS and CDNs
```

---

### 16.4 DNS Deep Dive

```yaml
dns:
  standard: RFC 1034 / RFC 1035
  record_types:
    - A (IPv4)
    - AAAA (IPv6)
    - CNAME (alias)
    - MX (mail)
    - TXT (arbitrary text, SPF, DKIM)
    - NS (nameserver)
    - SOA (start of authority)
    - SRV (service)
    - CAA (certification authority authorization)

  security_extensions:
    dnssec: RFC 4033
    doh: RFC 8484
    dot: RFC 7858

  split_horizon: Internal vs external DNS views
```

---

## 17. Testing Taxonomy & QA

```yaml
testing:
  description: >
    Formalized taxonomy of testing types and quality assurance standards.
  standards:
    - ISO 29119 (Software Testing)
    - IEEE 829 (Test Documentation)
    - IEEE 730 (Quality Assurance)
```

---

### 17.1 Testing Levels (ISO 29119)

```yaml
testing_levels:
  unit_testing:
    description: Test individual functions/methods in isolation
    isolation: mocks, stubs, fakes
    tools: [jest, pytest, cargo_test, junit, rspec]

  integration_testing:
    description: Test interaction between modules or services
    scope: [module_integration, API_integration, database_integration]

  system_testing:
    description: Test complete integrated system against requirements

  acceptance_testing:
    variants:
      uat: User Acceptance Testing
      alpha: Internal acceptance
      beta: External limited release
```

---

### 17.2 Testing Types

```yaml
testing_types:
  functional:
    - smoke_testing
    - regression_testing
    - sanity_testing
    - exploratory_testing

  non_functional:
    performance:
      - load_testing
      - stress_testing
      - soak_testing
      - spike_testing
      tools: [k6, locust, gatling, jmeter]

    security:
      - sast (Static Application Security Testing)
      - dast (Dynamic Application Security Testing)
      - iast (Interactive Application Security Testing)
      - fuzz_testing
      - penetration_testing

    reliability:
      - chaos_engineering
      - fault_injection
      tools: [chaos_monkey, litmus, toxiproxy]

    accessibility:
      standard: WCAG 2.2
      tools: [axe, lighthouse, wave]
```

---

### 17.3 Test-Driven Approaches

```yaml
test_driven:
  tdd:
    name: Test-Driven Development
    cycle: [red, green, refactor]

  bdd:
    name: Behaviour-Driven Development
    language: Gherkin (Given/When/Then)
    tools: [cucumber, behave, rspec]

  property_based_testing:
    description: Generate randomized inputs to find edge cases
    tools: [quickcheck, hypothesis, proptest]

  mutation_testing:
    description: Verify test quality by injecting code mutations
    tools: [stryker, pitest, cargo_mutants]
```

---

### 17.4 Code Coverage

```yaml
code_coverage:
  metrics:
    line_coverage: Lines executed
    branch_coverage: Decision branches taken
    statement_coverage: Statements executed
    mc_dc: Modified Condition/Decision Coverage (aerospace/safety-critical)

  thresholds:
    general: 80% line coverage minimum
    safety_critical: 100% MC/DC required (DO-178C)

  tools:
    rust: llvm_cov / cargo_tarpaulin
    javascript: istanbul / v8_coverage
    python: coverage_py
    java: jacoco
```

---

### 17.5 QA Standards

```yaml
qa_standards:
  iso_25010:
    name: Systems and Software Quality Requirements and Evaluation (SQuaRE)
    authority: iso
    reference: https://iso25000.com/
    characteristics:
      - functional_suitability
      - performance_efficiency
      - compatibility
      - usability
      - reliability
      - security
      - maintainability
      - portability

  ieee_730:
    name: Software Quality Assurance Processes
    authority: ieee
    reference: https://ieeexplore.ieee.org/document/8343633

  ieee_1012:
    name: Software Verification and Validation
    authority: ieee
    reference: https://ieeexplore.ieee.org/document/8055462
```

---

## 18. Reliability Engineering (SRE)

```yaml
sre:
  description: >
    Applying software engineering to operations problems.
    Practices from Google SRE Book and CNCF.
  reference: https://sre.google/
```

---

### 18.1 SRE Core Concepts

```yaml
sre_concepts:
  slo:
    name: Service Level Objective
    description: Target reliability level (e.g., 99.9% availability)

  sli:
    name: Service Level Indicator
    description: Measurement used to evaluate SLO (e.g., request success rate)

  sla:
    name: Service Level Agreement
    description: Contractual commitment to SLO with consequences

  error_budget:
    description: Allowable unreliability = 1 - SLO
    use: Gates deployment velocity

  toil:
    description: Manual, repetitive operational work to be automated
```

---

### 18.2 Incident Management

```yaml
incident_management:
  severity_levels:
    sev1: Complete service outage
    sev2: Major feature unavailable
    sev3: Minor degradation
    sev4: Low impact

  process:
    - detect (alerting)
    - respond (on-call rotation)
    - mitigate (reduce blast radius)
    - resolve (fix root cause)
    - postmortem (blameless, action items)

  postmortem:
    blameless: true
    components:
      - timeline
      - root_cause_analysis
      - contributing_factors
      - action_items
      - lessons_learned

  standards:
    itil: IT Infrastructure Library
    iso_20000:
      standard: ISO/IEC 20000
      authority: iso
```

---

### 18.3 Chaos Engineering

```yaml
chaos_engineering:
  principles:
    reference: Principles of Chaos Engineering
    url: https://principlesofchaos.org/
    steps:
      - define_steady_state
      - hypothesize
      - inject_failure
      - disprove_hypothesis

  tools:
    - chaos_monkey (Netflix)
    - litmus (CNCF)
    - toxiproxy (Shopify)
    - chaos_mesh (cncf)
    - aws_fault_injection_simulator
```

---

## 19. Security

```yaml
security:
  description: >
    Comprehensive security standards covering the full stack.
    Always loaded; applies to all domains.
  priority: highest
```

---

### 19.1 Secure SDLC

```yaml
secure_sdlc:
  microsoft_sdl:
    name: Microsoft Security Development Lifecycle
    reference: https://www.microsoft.com/en-us/securityengineering/sdl

  owasp_samm:
    name: Software Assurance Maturity Model
    authority: owasp
    reference: https://owaspsamm.org/

  nist_ssdf:
    name: Secure Software Development Framework
    authority: nist
    standard: NIST SP 800-218
    reference: https://csrc.nist.gov/publications/detail/sp/800-218/final

  bsimm:
    name: Building Security In Maturity Model
    type: descriptive_model

  phases:
    requirements: Threat modeling, security requirements
    design: Architecture review, attack surface analysis
    implementation: Secure coding, SAST
    testing: DAST, fuzzing, pentest
    deployment: Signed artifacts, hardened config
    operations: Monitoring, incident response, patch management
```

---

### 19.2 Threat Modeling

```yaml
threat_modeling:
  stride:
    authority: microsoft
    categories:
      S: Spoofing
      T: Tampering
      R: Repudiation
      I: Information Disclosure
      D: Denial of Service
      E: Elevation of Privilege

  pasta:
    name: Process for Attack Simulation and Threat Analysis
    stages: 7

  attack_trees:
    author: Bruce Schneier

  mitre_attack:
    authority: mitre
    reference: https://attack.mitre.org/
    components: [tactics, techniques, procedures]

  cvss:
    name: Common Vulnerability Scoring System
    version: "4.0"
    authority: first
    reference: https://www.first.org/cvss/
```

---

### 19.3 Common Vulnerabilities (CWE / OWASP)

```yaml
vulnerabilities:
  owasp_top_10:
    authority: owasp
    reference: https://owasp.org/www-project-top-ten/
    current_year: 2021
    items:
      A01: Broken Access Control
      A02: Cryptographic Failures
      A03: Injection
      A04: Insecure Design
      A05: Security Misconfiguration
      A06: Vulnerable and Outdated Components
      A07: Identification and Authentication Failures
      A08: Software and Data Integrity Failures
      A09: Security Logging and Monitoring Failures
      A10: Server-Side Request Forgery

  cwe_key:
    authority: mitre
    reference: https://cwe.mitre.org/
    critical_entries:
      CWE-20: Improper Input Validation
      CWE-22: Path Traversal
      CWE-77: Command Injection
      CWE-78: OS Command Injection
      CWE-79: Cross-Site Scripting
      CWE-89: SQL Injection
      CWE-94: Code Injection
      CWE-119: Buffer Overflow
      CWE-125: Out-of-bounds Read
      CWE-190: Integer Overflow
      CWE-269: Improper Privilege Management
      CWE-287: Improper Authentication
      CWE-306: Missing Authentication
      CWE-352: CSRF
      CWE-416: Use After Free
      CWE-502: Deserialization of Untrusted Data
      CWE-611: XXE Injection
      CWE-787: Out-of-bounds Write
      CWE-798: Hardcoded Credentials
      CWE-918: SSRF
```

---

### 19.4 Cryptography

```yaml
cryptography:
  standards:
    fips_140_3:
      name: Security Requirements for Cryptographic Modules
      authority: nist
      reference: https://csrc.nist.gov/publications/detail/fips/140/3/final

    nist_sp_800_131a:
      name: Transitioning Cryptographic Algorithms and Key Lengths
      authority: nist

  symmetric:
    aes:
      standard: FIPS 197
      key_lengths: [128, 192, 256]
      modes: [GCM, CCM, CBC, CTR]
    chacha20_poly1305:
      standard: RFC 8439

  asymmetric:
    rsa:
      standard: PKCS#1 (RFC 8017)
      min_key_length: 2048
    ecdsa:
      standard: FIPS 186-5
      curves: [P-256, P-384, P-521]
    ed25519:
      standard: RFC 8032
      recommended: true
    x25519:
      use_case: key_exchange

  post_quantum:
    ml_kem:
      name: Module-Lattice-Based Key Encapsulation
      standard: FIPS 203
      formerly: CRYSTALS-Kyber
    ml_dsa:
      name: Module-Lattice-Based Digital Signature
      standard: FIPS 204
      formerly: CRYSTALS-Dilithium
    slh_dsa:
      standard: FIPS 205
      formerly: SPHINCS+

  hashing:
    sha2:
      standard: FIPS 180-4
      variants: [SHA-224, SHA-256, SHA-384, SHA-512]
    sha3:
      standard: FIPS 202
      variants: [SHA3-224, SHA3-256, SHA3-384, SHA3-512, SHAKE128, SHAKE256]
    blake3:
      type: de_facto
      recommended: true
    argon2:
      standard: RFC 9106
      use_case: password_hashing

  pki:
    x509:
      standard: RFC 5280
    ca_browser_forum:
      reference: https://cabforum.org/
    ct:
      name: Certificate Transparency
      standard: RFC 9162
```

---

### 19.5 Identity & Access Management

```yaml
identity_access:
  authentication:
    oauth2:
      standard: RFC 6749
      authority: ietf
    oidc:
      name: OpenID Connect
      authority: openid
      reference: https://openid.net/specs/openid-connect-core-1_0.html
    saml2:
      standard: OASIS SAML 2.0
      use_case: enterprise_federation
    webauthn:
      authority: w3c
      reference: https://www.w3.org/TR/webauthn-2/
    passkeys:
      authority: [fido_alliance, w3c]
      based_on: webauthn

  authorization:
    rbac:
      name: Role-Based Access Control
      standard: NIST SP 800-207
    abac:
      name: Attribute-Based Access Control
    pbac:
      name: Policy-Based Access Control
    zanzibar:
      authority: google
      type: de_facto
      use_case: relationship_based_access_control
    opa:
      name: Open Policy Agent
      authority: cncf
      language: Rego

  token_standards:
    jwt:
      standard: RFC 7519
      authority: ietf
    jws:
      standard: RFC 7515
    jwe:
      standard: RFC 7516
    jwk:
      standard: RFC 7517

  zero_trust:
    standard: NIST SP 800-207
    authority: nist
    principles:
      - never_trust_always_verify
      - least_privilege
      - assume_breach
```

---

### 19.6 Supply Chain Security

```yaml
supply_chain_security:
  slsa:
    name: Supply Chain Levels for Software Artifacts
    authority: openssf
    reference: https://slsa.dev/spec/
    levels: [1, 2, 3]

  sbom:
    formats:
      spdx:
        authority: linux_foundation
        reference: https://spdx.dev/
        standard: ISO/IEC 5962
      cyclonedx:
        authority: owasp
        reference: https://cyclonedx.org/

  sigstore:
    authority: openssf
    components: [cosign, fulcio, rekor]
    reference: https://sigstore.dev/
    use_case: keyless_artifact_signing

  scorecard:
    authority: openssf
    reference: https://scorecard.dev/
    use_case: automated_oss_security_assessment

  dependency_auditing:
    tools:
      rust: cargo_audit / cargo_deny
      javascript: npm_audit / snyk
      python: pip_audit / safety
      java: dependency_check (OWASP)
```

---

### 19.7 Security Scanning Tools

```yaml
security_tooling:
  sast:
    - semgrep
    - codeql
    - bandit (python)
    - clippy (rust)
    - spotbugs (java)

  dast:
    - owasp_zap
    - burp_suite
    - nuclei

  container:
    - trivy
    - grype
    - snyk_container

  secrets:
    - trufflehog
    - gitleaks
    - detect_secrets
```

---

## 20. Observability

```yaml
observability:
  description: >
    The three pillars of observability: logs, metrics, and traces.
    Standards from OpenTelemetry (CNCF) and W3C.
  authority: cncf
  reference: https://opentelemetry.io/
```

---

### 20.1 OpenTelemetry (OTel)

```yaml
opentelemetry:
  authority: cncf
  reference: https://opentelemetry.io/docs/specs/
  components:
    api: Language-agnostic instrumentation API
    sdk: Reference implementation
    collector: Vendor-agnostic pipeline
    otlp:
      name: OpenTelemetry Protocol
      transport: [gRPC, HTTP/Protobuf]

  signals:
    traces: Distributed request flows
    metrics: Numeric measurements over time
    logs: Timestamped event records
    profiles: CPU/memory sampling (emerging)
    events: Structured point-in-time records (emerging)

  semantic_conventions:
    reference: https://opentelemetry.io/docs/specs/semconv/
    covers: [http, rpc, database, messaging, process, k8s]
```

---

### 20.2 Distributed Tracing

```yaml
distributed_tracing:
  w3c_trace_context:
    standard: W3C Trace Context Level 1
    authority: w3c
    reference: https://www.w3.org/TR/trace-context/
    headers: [traceparent, tracestate]

  w3c_baggage:
    standard: W3C Baggage
    authority: w3c
    reference: https://www.w3.org/TR/baggage/

  concepts:
    span: Single operation with start/end time
    trace: Directed acyclic graph of spans
    context_propagation: Passing trace context across service boundaries

  backends: [jaeger, zipkin, tempo, honeycomb, datadog]
```

---

### 20.3 Metrics

```yaml
metrics:
  prometheus:
    authority: cncf
    data_model: dimensional time series
    query_language: PromQL
    exposition_format: OpenMetrics
    reference: https://prometheus.io/

  openmetrics:
    authority: cncf
    reference: https://openmetrics.io/
    supersedes: Prometheus text format

  metric_types:
    counter: Monotonically increasing
    gauge: Point-in-time value
    histogram: Distribution of values
    summary: Client-calculated quantiles

  use_red_method:
    applies_to: services
    dimensions: [Rate, Errors, Duration]

  use_use_method:
    applies_to: resources
    dimensions: [Utilization, Saturation, Errors]
```

---

### 20.4 Logging

```yaml
logging:
  formats:
    structured: JSON preferred
    ecs:
      name: Elastic Common Schema
      reference: https://www.elastic.co/guide/en/ecs/
    cef:
      name: Common Event Format
      use_case: SIEM integration

  levels:
    - TRACE
    - DEBUG
    - INFO
    - WARN
    - ERROR
    - FATAL

  syslog:
    standard: RFC 5424
    authority: ietf

  best_practices:
    - Never log secrets or PII
    - Include trace context (trace_id, span_id)
    - Use structured fields, not format strings
    - Correlate with metrics and traces

  backends: [elasticsearch, loki, splunk, cloudwatch]
```

---

### 20.5 Alerting & Dashboarding

```yaml
alerting:
  tools: [alertmanager, pagerduty, opsgenie, victorops]
  alerting_fatigue: Avoid via noise reduction and SLO-based alerts

dashboarding:
  tools: [grafana, kibana, datadog]
  grafana:
    authority: grafana_labs
    supports: [prometheus, loki, tempo, influxdb, elasticsearch]
```

---

## 21. UX & Accessibility

```yaml
ux_accessibility:
  description: >
    Standards for usability, accessibility, and human-centred design.
```

---

### 21.1 Accessibility Standards (WCAG)

```yaml
wcag:
  current_version: "2.2"
  authority: w3c
  reference: https://www.w3.org/TR/WCAG22/

  principles:
    P: Perceivable
    O: Operable
    U: Understandable
    R: Robust

  levels:
    A: Minimum
    AA: Standard (legally required in most jurisdictions)
    AAA: Enhanced

  wcag_3:
    status: draft
    reference: https://www.w3.org/TR/wcag-3.0/
    scoring_model: functional_outcomes

  related:
    aria:
      reference: https://www.w3.org/TR/wai-aria-1.2/
    atag:
      name: Authoring Tool Accessibility Guidelines
      reference: https://www.w3.org/TR/ATAG20/
    uaag:
      name: User Agent Accessibility Guidelines
      reference: https://www.w3.org/TR/UAAG20/
```

---

### 21.2 Legal Accessibility Requirements

```yaml
accessibility_law:
  ada:
    name: Americans with Disabilities Act
    jurisdiction: USA
    applies_to: public_accommodations

  section_508:
    name: Section 508 (Rehabilitation Act)
    jurisdiction: USA
    applies_to: federal_government

  en_301_549:
    name: EN 301 549
    jurisdiction: EU
    reference: https://www.etsi.org/deliver/etsi_en/301500_302000/301549/

  aoda:
    name: Accessibility for Ontarians with Disabilities Act
    jurisdiction: Canada

  eaa:
    name: European Accessibility Act
    jurisdiction: EU
    effective: 2025
```

---

### 21.3 UX Standards

```yaml
ux_standards:
  iso_9241:
    name: Ergonomics of Human-System Interaction
    authority: iso
    parts:
      110: Dialogue Principles
      210: Human-Centred Design for Interactive Systems
    reference: https://www.iso.org/standard/77520.html

  interaction_design_patterns:
    - progressive_disclosure
    - confirmation_dialogs
    - undo_redo
    - empty_states
    - skeleton_screens
    - optimistic_ui

  design_systems:
    examples:
      - Material Design (Google)
      - Human Interface Guidelines (Apple)
      - Fluent Design (Microsoft)
      - Carbon (IBM)
```

---

### 21.4 Internationalisation

```yaml
internationalisation:
  unicode:
    authority: unicode_consortium
    standard: Unicode Standard
    reference: https://unicode.org/standard/standard.html
    bidi: Unicode Bidirectional Algorithm (UBA)

  cldr:
    name: Common Locale Data Repository
    authority: unicode_consortium
    reference: https://cldr.unicode.org/

  icu:
    name: International Components for Unicode
    reference: https://icu.unicode.org/

  ecma_i18n:
    standard: ECMA-402
    reference: https://tc39.es/ecma402/

  bcp47:
    name: Language Tags
    standard: RFC 5646
    authority: ietf
```

---

## 22. AI & Data Systems

```yaml
ai_data:
  description: >
    Standards and practices for machine learning, model governance,
    and data lifecycle management.
```

---

### 22.1 ML Lifecycle

```yaml
ml_lifecycle:
  phases:
    - data_collection
    - data_preparation
    - feature_engineering
    - model_training
    - model_evaluation
    - model_deployment
    - model_monitoring
    - model_retirement

  mlops:
    description: DevOps practices applied to ML pipelines
    tools: [mlflow, kubeflow, metaflow, zenml, bentoml]

  experiment_tracking:
    tools: [mlflow, wandb, neptune, comet_ml]

  model_serving:
    formats: [onnx, tensorflow_savedmodel, torchscript]
    servers: [triton, torchserve, tensorflow_serving, bento]
```

---

### 22.2 Model Governance & Responsible AI

```yaml
model_governance:
  explainability:
    techniques: [SHAP, LIME, integrated_gradients, attention_maps]

  fairness:
    dimensions: [demographic_parity, equalized_odds, individual_fairness]
    tools: [fairlearn, aif360, what_if_tool]

  eu_ai_act:
    authority: european_union
    status: enacted_2024
    risk_tiers: [unacceptable, high, limited, minimal]
    reference: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689

  nist_ai_rmf:
    name: AI Risk Management Framework
    authority: nist
    reference: https://airc.nist.gov/Home

  model_cards:
    authority: google
    reference: https://modelcards.withgoogle.com/

  datasheets_for_datasets:
    reference: Gebru et al. (2021)
```

---

### 22.3 Data Formats & Interchange (AI/ML)

```yaml
ml_data_formats:
  onnx:
    name: Open Neural Network Exchange
    authority: linux_foundation
    reference: https://onnx.ai/
    use_case: model_portability

  hdf5:
    use_case: [weights_storage, dataset_storage]

  arrow:
    authority: apache
    use_case: in_memory_columnar_for_ml

  parquet:
    authority: apache
    use_case: training_data_storage

  jsonlines:
    use_case: streaming_training_data
```

---

## 23. Governance & Compliance

```yaml
governance:
  description: >
    Legal, regulatory, and audit frameworks governing software systems.
```

---

### 23.1 Risk Management

```yaml
risk_management:
  iso_31000:
    name: Risk Management — Guidelines
    authority: iso
    reference: https://www.iso.org/standard/65694.html

  nist_rmf:
    name: Risk Management Framework
    authority: nist
    standard: NIST SP 800-37

  fair:
    name: Factor Analysis of Information Risk
    use_case: quantitative_risk_modeling
```

---

### 23.2 Security Compliance Frameworks

```yaml
security_compliance:
  iso_27001:
    name: Information Security Management
    authority: iso
    reference: https://www.iso.org/standard/27001

  soc2:
    name: Service Organization Control 2
    authority: aicpa
    trust_criteria: [security, availability, confidentiality, processing_integrity, privacy]

  pci_dss:
    name: Payment Card Industry Data Security Standard
    authority: pci_ssc
    version: "4.0"
    reference: https://www.pcisecuritystandards.org/

  fedramp:
    name: Federal Risk and Authorization Management Program
    jurisdiction: USA
    applies_to: cloud_services_to_federal_agencies

  hipaa:
    name: Health Insurance Portability and Accountability Act
    jurisdiction: USA
    applies_to: health_data

  gdpr:
    name: General Data Protection Regulation
    authority: european_union
    reference: https://gdpr.eu/
    key_rights: [access, erasure, portability, objection]

  nist_csf:
    name: Cybersecurity Framework
    authority: nist
    version: "2.0"
    reference: https://www.nist.gov/cyberframework
    functions: [govern, identify, protect, detect, respond, recover]
```

---

### 23.3 Audit & Documentation Standards

```yaml
audit_standards:
  iso_15408:
    name: Common Criteria for IT Security Evaluation
    authority: [iso, iec]
    reference: https://www.commoncriteriaportal.org/

  soc1:
    name: Service Organization Control 1
    authority: aicpa
    applies_to: financial_controls

  iso_20000:
    name: IT Service Management
    authority: iso

  iso_12207:
    name: Software Life Cycle Processes
    authority: [iso, iec, ieee]
    reference: https://www.iso.org/standard/63712.html

  iso_15288:
    name: System Life Cycle Processes
    authority: [iso, iec, ieee]
    reference: https://www.iso.org/standard/81702.html
```

---

## 24. Meta Layer

```yaml
meta:
  description: >
    Documentation standards, versioning, and project-level governance.
```

---

### 24.1 Semantic Versioning

```yaml
versioning:
  semver:
    authority: semver_org
    format: MAJOR.MINOR.PATCH
    rules:
      major: Incompatible API changes
      minor: Backward-compatible new features
      patch: Backward-compatible bug fixes
    reference: https://semver.org/

  calver:
    description: Calendar-based versioning (YYYY.MM.DD)
    use_case: rolling_release_projects

  pre_release:
    tags: [alpha, beta, rc]
    format: 1.0.0-alpha.1
```

---

### 24.2 Documentation Standards

```yaml
documentation:
  docstring_standards:
    rust: rustdoc (///, //!)
    python: pep257 / numpydoc / google_style
    java: javadoc
    javascript: jsdoc

  specification_formats:
    openapi: REST API docs
    asyncapi: Async API docs
    arc42: Architecture docs
    adr: Architecture Decision Records

  diagramming:
    c4_model: https://c4model.com/
    uml:
      authority: omg
      reference: https://www.omg.org/spec/UML/
    mermaid:
      type: de_facto
      use_case: code_embedded_diagrams
    plantuml:
      type: de_facto

  changelog:
    keep_a_changelog:
      reference: https://keepachangelog.com/
    conventional_commits:
      reference: https://www.conventionalcommits.org/
```

---

### 24.3 Licensing

```yaml
licensing:
  spdx_identifiers:
    authority: linux_foundation
    reference: https://spdx.org/licenses/

  common_licenses:
    permissive:
      - MIT
      - Apache-2.0
      - BSD-2-Clause
      - BSD-3-Clause
    copyleft:
      - GPL-2.0-only
      - GPL-3.0-only
      - LGPL-2.1-only
      - AGPL-3.0-only
    weak_copyleft:
      - MPL-2.0
    patent_grants:
      - Apache-2.0 (explicit)
      - GPL-3.0 (explicit)

  compatibility_matrix:
    note: Apache-2.0 is incompatible with GPL-2.0; compatible with GPL-3.0
    reference: https://www.gnu.org/licenses/license-compatibility.html
```

---

### 24.4 Code Quality & Formatting

```yaml
code_quality:
  linting:
    rust: clippy
    javascript: eslint / oxlint
    python: ruff / pylint
    go: golangci-lint
    general: semgrep

  formatting:
    rust: rustfmt
    javascript: prettier
    python: black / ruff format
    go: gofmt

  complexity:
    cyclomatic_complexity:
      description: McCabe's cyclomatic complexity
      threshold: <= 10 recommended

    cognitive_complexity:
      authority: sonarqube
      description: More intuitive measure of code understandability

  static_analysis:
    standards: [CWE, CERT, MISRA C (safety-critical)]
```

---

### 24.5 Project Health Metrics

```yaml
project_health:
  openssf_scorecard:
    authority: openssf
    reference: https://scorecard.dev/
    checks:
      - branch_protection
      - ci_tests
      - cii_best_practices
      - code_review
      - contributors
      - dangerous_workflow
      - dependency_update_tool
      - fuzzing
      - license
      - maintained
      - pinned_dependencies
      - sast
      - security_policy
      - signed_releases
      - token_permissions
      - vulnerabilities

  cii_best_practices:
    authority: openssf
    reference: https://www.bestpractices.dev/
    levels: [passing, silver, gold]
```

---

*End of Global Software Engineering Standards Ontology v3.0*
