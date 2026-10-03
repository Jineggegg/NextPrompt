import pytest

from nextprompt.hook import generate_suggestion
from nextprompt.redact import redact
from nextprompt.transcript import Message

# All credentials in tests are deliberately fake.
SECRETS = [
    "sk-test-example-not-real",
    "sk-ant-test-example-not-real",
    "ghp_fake_example_not_real",
    "github_pat_fake_example_not_real",
    "AKIAFAKEEXAMPLE1234567",
    "sk_live_fake_example",
    "sk_test_fake_example",
    "rk_live_fake_example",
    "rk_test_fake_example",
    "Authorization: Bearer fake.example.token",
    "PASSWORD=fake-password",
    "API_KEY='fake-api-value'",
    'SECRET="fake-secret-value"',
    "TOKEN=fake-token",
    "AWS_SECRET_ACCESS_KEY=fake-secret",
    "-----BEGIN PRIVATE KEY-----\nFAKE\n-----END PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----\nFAKE\n-----END RSA PRIVATE KEY-----",
    "-----BEGIN PRIVATE KEY-----\nFAKE incomplete",
]


@pytest.mark.parametrize("secret", SECRETS)
def test_redaction(secret):
    value = redact("Please check " + secret + "\nNext instruction.")
    assert secret not in value
    assert "[REDACTED]" in value


@pytest.mark.parametrize("secret", SECRETS)
def test_provider_never_receives_secret(secret, configured, provider, clipboard):
    messages = [
        Message("user", "Fix auth using " + secret),
        Message("assistant", "The redirect fix is implemented. Targeted tests pass."),
    ]
    generate_suggestion(messages, configured.load(), configured, provider, clipboard)
    context = provider.generate.call_args.args[0]
    assert secret not in context
    assert "FAKEKEYDATA" not in context


def test_ordinary_prose_is_preserved():
    assert (
        redact("Run the full regression suite and review the final diff.")
        == "Run the full regression suite and review the final diff."
    )
