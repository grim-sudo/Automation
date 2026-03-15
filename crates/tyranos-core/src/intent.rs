//! NLP intent detection engine — ported from tyranos/nlp/semantic_engine.py.
//!
//! Uses compiled regexes (via once_cell::sync::Lazy) to classify
//! natural-language commands into typed intents with confidence scores.

use once_cell::sync::Lazy;
use regex::RegexSet;
use serde::{Deserialize, Serialize};

/// All supported intent categories.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum IntentType {
    Create,
    Delete,
    Modify,
    Query,
    Execute,
    Configure,
    Analyze,
    Help,
    N8nWorkflow,
    BuildDistro,
    Unknown,
}

impl std::fmt::Display for IntentType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match self {
            Self::Create => "create",
            Self::Delete => "delete",
            Self::Modify => "modify",
            Self::Query => "query",
            Self::Execute => "execute",
            Self::Configure => "configure",
            Self::Analyze => "analyze",
            Self::Help => "help",
            Self::N8nWorkflow => "n8n_workflow",
            Self::BuildDistro => "build_distro",
            Self::Unknown => "unknown",
        };
        write!(f, "{s}")
    }
}

/// A named entity extracted from the command.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entity {
    pub kind: String,
    pub value: String,
}

/// The result of NLP intent classification.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentResult {
    pub intent: IntentType,
    pub confidence: f32,
    pub entities: Vec<Entity>,
    pub corrected_command: Option<String>,
}

// ── Compiled regex sets (one per intent) ──────────────────────────────────────

static CREATE_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\b(create|make|generate|scaffold|build|setup|new|init|initialise|initialize|add|write)\b",
        r"(?i)\b(project|folder|directory|file|template|boilerplate|skeleton)\b",
        r"(?i)\b(python|rust|go|java|react|express|flask|django|fastapi)\s+(project|app|service)\b",
    ])
    .expect("CREATE_PATTERNS regex compile failed")
});

static DELETE_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\b(delete|remove|erase|purge|wipe|uninstall|clean|clear|drop|destroy)\b",
        r"(?i)\b(file|folder|directory|package|service|database|table|index)\b",
    ])
    .expect("DELETE_PATTERNS regex compile failed")
});

static MODIFY_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\b(move|copy|rename|update|convert|transform|migrate|transfer|modify|change|edit)\b",
        r"(?i)\b(file|folder|directory|config|setting|record)\b",
    ])
    .expect("MODIFY_PATTERNS regex compile failed")
});

static QUERY_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\b(show|list|find|search|check|status|display|get|fetch|read|view|scan|ls|dir)\b",
        r"(?i)\b(file|folder|process|service|port|network|disk|memory|cpu|system)\b",
    ])
    .expect("QUERY_PATTERNS regex compile failed")
});

static EXECUTE_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\b(run|start|execute|launch|trigger|deploy|release|publish|ship|activate|enable)\b",
        r"(?i)\b(script|command|workflow|pipeline|job|task|service|container)\b",
    ])
    .expect("EXECUTE_PATTERNS regex compile failed")
});

static CONFIGURE_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\b(configure|enable|disable|set|tune|adjust|toggle|install|setup)\b",
        r"(?i)\b(service|setting|option|config|flag|feature|firewall|permission)\b",
    ])
    .expect("CONFIGURE_PATTERNS regex compile failed")
});

static ANALYZE_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\b(analyze|analyse|audit|inspect|review|assess|measure|monitor|profile|benchmark)\b",
        r"(?i)\b(performance|security|code|log|metric|dependency|vulnerability)\b",
    ])
    .expect("ANALYZE_PATTERNS regex compile failed")
});

static HELP_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\b(help|assist|support|guide|how|what|explain|describe)\b",
        r"(?i)(what can you do|how do i|show commands|available commands)",
    ])
    .expect("HELP_PATTERNS regex compile failed")
});

static N8N_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\bn8n\b",
        r"(?i)\b(workflow|automation)\b",
        r"(?i)\b(webhook|trigger|node|integration)\b",
        r"(?i)\b(list workflows|create workflow|run workflow|trigger workflow)\b",
    ])
    .expect("N8N_PATTERNS regex compile failed")
});

static DISTRO_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)\b(build|create|generate|compile)\b.*(iso|distro|distribution|linux image|os image)\b",
        r"(?i)\b(debian|arch|ubuntu|alpine|fedora)\s+(iso|image|distro)\b",
        r"(?i)\b(custom linux|custom os|linux iso|bootable)\b",
        r"(?i)\biso\b",
    ])
    .expect("DISTRO_PATTERNS regex compile failed")
});

// ── NLP Engine ────────────────────────────────────────────────────────────────

/// Classifies natural-language commands into typed intents.
pub struct NlpEngine;

impl NlpEngine {
    pub fn new() -> Self {
        // Force lazy initialisation at construction time so first call is fast.
        let _ = &*CREATE_PATTERNS;
        let _ = &*DELETE_PATTERNS;
        let _ = &*N8N_PATTERNS;
        let _ = &*DISTRO_PATTERNS;
        Self
    }

    /// Parse a command string and return an `IntentResult`.
    pub fn parse(&self, command: &str) -> IntentResult {
        let cmd = command.trim().to_lowercase();

        // Ordered by specificity — more specific patterns checked first.
        let matches: &[(IntentType, &Lazy<RegexSet>, f32)] = &[
            (IntentType::BuildDistro, &DISTRO_PATTERNS, 0.92),
            (IntentType::N8nWorkflow, &N8N_PATTERNS, 0.90),
            (IntentType::Help, &HELP_PATTERNS, 0.95),
            (IntentType::Create, &CREATE_PATTERNS, 0.88),
            (IntentType::Delete, &DELETE_PATTERNS, 0.90),
            (IntentType::Analyze, &ANALYZE_PATTERNS, 0.88),
            (IntentType::Configure, &CONFIGURE_PATTERNS, 0.85),
            (IntentType::Execute, &EXECUTE_PATTERNS, 0.85),
            (IntentType::Modify, &MODIFY_PATTERNS, 0.82),
            (IntentType::Query, &QUERY_PATTERNS, 0.85),
        ];

        for (intent, pattern_set, base_confidence) in matches {
            let matched = pattern_set.matches(&cmd);
            let match_count =
                matched.matched_any() as usize + matched.iter().count().saturating_sub(1);
            if match_count > 0 {
                // Boost confidence for each additional pattern that matched.
                let confidence = (*base_confidence + 0.02 * (match_count as f32 - 1.0)).min(0.99);
                return IntentResult {
                    intent: intent.clone(),
                    confidence,
                    entities: Vec::new(),
                    corrected_command: None,
                };
            }
        }

        IntentResult {
            intent: IntentType::Unknown,
            confidence: 0.0,
            entities: Vec::new(),
            corrected_command: None,
        }
    }
}

impl Default for NlpEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_intent() {
        let eng = NlpEngine::new();
        let r = eng.parse("create a folder named test");
        assert_eq!(r.intent, IntentType::Create);
        assert!(r.confidence > 0.8);
    }

    #[test]
    fn test_delete_intent() {
        let eng = NlpEngine::new();
        let r = eng.parse("delete all temp files");
        assert_eq!(r.intent, IntentType::Delete);
        assert!(r.confidence > 0.8);
    }

    #[test]
    fn test_distro_intent() {
        let eng = NlpEngine::new();
        let r = eng.parse("build a minimal debian iso");
        assert_eq!(r.intent, IntentType::BuildDistro);
        assert!(r.confidence > 0.85);
    }

    #[test]
    fn test_n8n_intent() {
        let eng = NlpEngine::new();
        let r = eng.parse("list all n8n workflows");
        assert_eq!(r.intent, IntentType::N8nWorkflow);
    }
}
