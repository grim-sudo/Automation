//! Integration tests for tyranos-core.

use tyranos_core::{
    config::Config,
    intent::{IntentType, NlpEngine},
    security::PathValidator,
};

#[test]
fn test_intent_create() {
    let nlp = NlpEngine::new();
    let result = nlp.parse("create folder test");
    assert_eq!(result.intent, IntentType::Create);
    assert!(
        result.confidence >= 0.80,
        "confidence was {}",
        result.confidence
    );
}

#[test]
fn test_intent_delete() {
    let nlp = NlpEngine::new();
    let result = nlp.parse("delete temp files");
    assert_eq!(result.intent, IntentType::Delete);
    assert!(result.confidence >= 0.80);
}

#[test]
fn test_intent_distro() {
    let nlp = NlpEngine::new();
    let result = nlp.parse("build debian iso");
    assert_eq!(result.intent, IntentType::BuildDistro);
    assert!(result.confidence >= 0.85);
}

#[test]
fn test_intent_n8n() {
    let nlp = NlpEngine::new();
    let result = nlp.parse("list all n8n workflows");
    assert_eq!(result.intent, IntentType::N8nWorkflow);
}

#[test]
fn test_path_traversal_blocked() {
    let v = PathValidator::permissive();
    assert!(v.validate("../etc/passwd").is_err());
    assert!(v.validate("foo/../../etc/passwd").is_err());
}

#[test]
fn test_path_safe() {
    let v = PathValidator::permissive();
    assert!(v.validate("/tmp/test").is_ok());
}

#[test]
fn test_config_load_defaults() {
    let cfg = Config::default();
    assert_eq!(cfg.ai.max_tokens, 8000);
    assert_eq!(cfg.n8n.url, "http://localhost:5678");
    assert!(!cfg.debug);
}

#[test]
fn test_config_env_override() {
    // Set a predictable env var and verify it overrides the default.
    std::env::set_var("OPENROUTER_API_KEY", "test-key-12345");
    let cfg = Config::load().unwrap_or_default();
    assert_eq!(cfg.ai.openrouter_api_key, "test-key-12345");
    std::env::remove_var("OPENROUTER_API_KEY");
}
