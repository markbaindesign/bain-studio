import json
import time
from unittest import mock

import pytest

from studio import linkedin_post as lp


@pytest.fixture
def token_file(tmp_path, monkeypatch):
    path = tmp_path / 'linkedin_token.json'
    monkeypatch.setattr(lp, 'TOKEN_PATH', path)
    token = {'access_token': 'tok', 'expires_at': int(time.time()) + 30 * 86400,
             'person_urn': 'urn:li:person:abc', 'name': 'Mark Bain', 'scope': ''}
    path.write_text(json.dumps(token))
    return path


def _resp(status=201, body=None, headers=None):
    r = mock.Mock(ok=200 <= status < 300, status_code=status, headers=headers or {})
    r.json.return_value = body or {}
    r.text = json.dumps(body or {})
    return r


# ── text ──

def test_escapes_reserved_characters():
    assert lp.to_commentary('Fast (really) & cheap_ish') == 'Fast \\(really\\) & cheap\\_ish'


def test_hashtags_become_templates():
    assert lp.to_commentary('Shipped it #WordPress') == 'Shipped it {hashtag|\\#|WordPress}'


def test_hash_inside_word_is_escaped_not_tagged():
    assert lp.to_commentary('issue#42 and C# code') == 'issue\\#42 and C\\# code'


def test_backslash_escaped_first_class():
    assert lp.to_commentary('a\\b') == 'a\\\\b'


def test_lint_flags_mdash_length_and_hashtags():
    warnings = lp.lint('one — two #a #b #c' + 'x' * 3000)
    assert len(warnings) == 3


def test_lint_clean_text():
    assert lp.lint('A plain post - with a hyphen. #craft') == []


# ── token ──

def test_missing_token_tells_you_to_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, 'TOKEN_PATH', tmp_path / 'nope.json')
    with pytest.raises(lp.LinkedInError, match='auth'):
        lp.load_token()


def test_expired_token_refused(token_file):
    data = json.loads(token_file.read_text())
    data['expires_at'] = int(time.time()) - 1
    token_file.write_text(json.dumps(data))
    with pytest.raises(lp.LinkedInError, match='expired'):
        lp.load_token()


def test_save_token_is_private(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, 'TOKEN_PATH', tmp_path / 'sub' / 't.json')
    lp.save_token({'expires_at': 1})
    assert (tmp_path / 'sub' / 't.json').stat().st_mode & 0o777 == 0o600


# ── post ──

def test_dry_run_is_default_and_sends_nothing(token_file, capsys):
    with mock.patch.object(lp.requests, 'post') as post, mock.patch.object(lp.requests, 'put') as put:
        assert lp.main(['post', 'Hello (world)']) == 0
    post.assert_not_called()
    put.assert_not_called()
    assert 'Dry run' in capsys.readouterr().out


def test_publish_text_post(token_file, capsys):
    with mock.patch.object(lp.requests, 'post',
                           return_value=_resp(201, headers={'x-restli-id': 'urn:li:share:1'})) as post:
        assert lp.main(['post', 'Hello #craft', '--yes']) == 0
    url, kwargs = post.call_args.args[0], post.call_args.kwargs
    assert url == 'https://api.linkedin.com/rest/posts'
    assert kwargs['headers']['LinkedIn-Version'] == lp.API_VERSION
    assert kwargs['headers']['X-Restli-Protocol-Version'] == '2.0.0'
    body = kwargs['json']
    assert body['author'] == 'urn:li:person:abc'
    assert body['commentary'] == 'Hello {hashtag|\\#|craft}'
    assert body['lifecycleState'] == 'PUBLISHED'
    assert 'content' not in body
    assert 'https://www.linkedin.com/feed/update/urn:li:share:1/' in capsys.readouterr().out


def test_publish_with_image(token_file, tmp_path):
    img = tmp_path / 'a.png'
    img.write_bytes(b'png')
    init = _resp(200, {'value': {'uploadUrl': 'https://up', 'image': 'urn:li:image:X'}})
    created = _resp(201, headers={'x-restli-id': 'urn:li:share:2'})
    with mock.patch.object(lp.requests, 'post', side_effect=[init, created]) as post, \
         mock.patch.object(lp.requests, 'put', return_value=_resp(201)) as put:
        assert lp.main(['post', 'Pic', '--image', str(img), '--alt', 'a cat', '--yes']) == 0
    assert post.call_args_list[0].kwargs['json'] == {'initializeUploadRequest': {'owner': 'urn:li:person:abc'}}
    assert put.call_args.args[0] == 'https://up'
    assert put.call_args.kwargs['data'] == b'png'
    assert post.call_args_list[1].kwargs['json']['content'] == {'media': {'id': 'urn:li:image:X', 'altText': 'a cat'}}


def test_api_error_returns_nonzero(token_file, capsys):
    with mock.patch.object(lp.requests, 'post', return_value=_resp(401, {'message': 'bad'})):
        assert lp.main(['post', 'x', '--yes']) == 1
    assert 'Run: python3 studio/linkedin_post.py auth' in capsys.readouterr().err


def test_missing_image_fails_before_any_call(token_file):
    with mock.patch.object(lp.requests, 'post') as post:
        assert lp.main(['post', 'x', '--image', '/nope.png', '--yes']) == 1
    post.assert_not_called()
