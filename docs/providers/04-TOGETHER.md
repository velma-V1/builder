# Providers 04 — Together

Config: base `https://api.together.xyz/v1`, approved domain `api.together.xyz`, secret
`TOGETHER_API_KEY`. Requires an exact approved serverless model **or** a dedicated-endpoint id. The
endpoint identity (serverless vs dedicated) is preserved on the fingerprint. Only documented
parameters are sent; unsupported parameters fail closed at the core capability gate. Tools /
structured output / streaming are honored only when advertised.
