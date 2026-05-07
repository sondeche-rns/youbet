"""
Flask HTTP layer tests: request validation and algorithm factory.
Tests verify behavior through the public HTTP interface only.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_client():
    """Return a Flask test client with TESTING mode enabled."""
    import app as flask_app
    flask_app.app.config['TESTING'] = True
    return flask_app.app.test_client()


# ---------------------------------------------------------------------------
# Slice 1 & 2: POST /api/predict — missing required fields
# ---------------------------------------------------------------------------

class TestPredictValidation(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_missing_home_team_returns_400(self):
        resp = self.client.post(
            '/api/predict',
            data=json.dumps({'away_team': 'Arsenal'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertEqual(body['error'], 'Missing required fields')
        self.assertIn('home_team', body['missing'])

    def test_missing_away_team_returns_400(self):
        resp = self.client.post(
            '/api/predict',
            data=json.dumps({'home_team': 'Chelsea'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertEqual(body['error'], 'Missing required fields')
        self.assertIn('away_team', body['missing'])

    def test_missing_both_fields_lists_both(self):
        resp = self.client.post(
            '/api/predict',
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertIn('home_team', body['missing'])
        self.assertIn('away_team', body['missing'])

    def test_valid_request_returns_200(self):
        fake_prediction = {
            'homeWinProb': 0.5, 'drawProb': 0.25, 'awayWinProb': 0.25,
            'confidence': 0.7, 'recommendation': {'outcome': 'Home', 'expectedValue': 0.1, 'recommendation': 'Bet'},
        }
        with patch('app.get_algorithm') as mock_factory:
            mock_algo = MagicMock()
            mock_algo.predict_match.return_value = fake_prediction
            mock_factory.return_value = mock_algo

            resp = self.client.post(
                '/api/predict',
                data=json.dumps({'home_team': 'Chelsea', 'away_team': 'Arsenal'}),
                content_type='application/json',
            )
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Slice 4: POST /api/fixtures/live-odds — missing required fields
# ---------------------------------------------------------------------------

class TestLiveOddsValidation(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_missing_home_team_returns_400(self):
        resp = self.client.post(
            '/api/fixtures/live-odds',
            data=json.dumps({'away_team': 'Arsenal'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertEqual(body['error'], 'Missing required fields')
        self.assertIn('home_team', body['missing'])

    def test_missing_away_team_returns_400(self):
        resp = self.client.post(
            '/api/fixtures/live-odds',
            data=json.dumps({'home_team': 'Chelsea'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertEqual(body['error'], 'Missing required fields')
        self.assertIn('away_team', body['missing'])


# ---------------------------------------------------------------------------
# Slice 5: POST /api/jackpots/results — missing required fields
# ---------------------------------------------------------------------------

class TestJackpotResultsValidation(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_missing_jackpot_id_returns_400(self):
        resp = self.client.post(
            '/api/jackpots/results',
            data=json.dumps({'results': ['1', '2']}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertEqual(body['error'], 'Missing required fields')
        self.assertIn('jackpot_id', body['missing'])

    def test_missing_results_returns_400(self):
        resp = self.client.post(
            '/api/jackpots/results',
            data=json.dumps({'jackpot_id': 'jp-001'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertEqual(body['error'], 'Missing required fields')
        self.assertIn('results', body['missing'])


if __name__ == '__main__':
    unittest.main()
