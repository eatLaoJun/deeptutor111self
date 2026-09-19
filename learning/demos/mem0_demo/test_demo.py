import unittest
from unittest.mock import Mock

from demo import build_config, execute, parser


class DemoTests(unittest.TestCase):
    def test_turn_scope_never_calls_backend(self):
        backend = Mock()
        args = parser().parse_args(["add", "brief this time", "--scope", "turn"])
        self.assertFalse(execute(backend, args)["persisted"])
        self.assertEqual(backend.mock_calls, [])

    def test_add_only_sends_user_message(self):
        backend = Mock()
        backend.add.return_value = {"results": []}
        args = parser().parse_args(["--user", "alice", "add", "prefer hints"])
        execute(backend, args)
        self.assertEqual(backend.add.call_args.kwargs["user_id"], "alice")
        self.assertEqual(backend.add.call_args.args[0][0]["role"], "user")

    def test_false_success_add_is_rejected(self):
        backend = Mock()
        backend.add.return_value = {"results": [{"id": "missing", "event": "ADD"}]}
        backend.get.return_value = None
        from unittest.mock import patch
        with patch("demo.time.sleep"), self.assertRaises(ValueError):
            execute(backend, parser().parse_args(["add", "prefer hints"]))

    def test_search_is_scoped(self):
        backend = Mock()
        execute(backend, parser().parse_args(["--user", "bob", "search", "preferences"]))
        self.assertEqual(backend.search.call_args.kwargs["filters"], {"user_id": "bob"})

    def test_cross_user_mutation_rejected(self):
        for command in (["update", "id", "new"], ["delete", "id", "--yes"], ["history", "id"]):
            backend = Mock()
            backend.get.return_value = {"user_id": "someone_else"}
            with self.assertRaises(ValueError):
                execute(backend, parser().parse_args(command))
            backend.update.assert_not_called()
            backend.delete.assert_not_called()
            backend.history.assert_not_called()

    def test_delete_requires_confirmation(self):
        backend = Mock()
        backend.get.return_value = {"user_id": "student_a"}
        with self.assertRaises(ValueError):
            execute(backend, parser().parse_args(["delete", "id"]))
        backend.delete.assert_not_called()

    def test_update_and_history(self):
        backend = Mock()
        backend.get.return_value = {"user_id": "student_a"}
        execute(backend, parser().parse_args(["update", "id", "new"]))
        backend.update.assert_called_once_with(memory_id="id", text="new")
        execute(backend, parser().parse_args(["history", "id"]))
        backend.history.assert_called_once_with(memory_id="id")

    def test_shared_key_and_precedence(self):
        settings = dict(llm_model="chat", llm_base_url="https://example.test/v1",
                        embedding_model="embed", embedding_base_url="https://example.test/v1",
                        embedding_dims=3, api_key="shared-test")
        config = build_config(settings, {})
        self.assertEqual(config["llm"]["config"]["api_key"], "shared-test")
        self.assertEqual(config["embedder"]["config"]["api_key"], "shared-test")
        settings["embedding_api_key"] = "embedding-test"
        config = build_config(settings, {"DEMO_LLM_API_KEY": "environment-test"})
        self.assertEqual(config["llm"]["config"]["api_key"], "environment-test")
        self.assertEqual(config["embedder"]["config"]["api_key"], "embedding-test")

    def test_config_has_explicit_paths_and_credentials(self):
        settings = dict(llm_model="chat", llm_base_url="https://example.test/v1",
                        embedding_model="embed", embedding_base_url="https://example.test/v1",
                        embedding_dims=1024)
        config = build_config(settings, dict(DEMO_LLM_API_KEY="test", DEMO_EMBEDDING_API_KEY="test"))
        self.assertEqual(config["vector_store"]["config"]["embedding_model_dims"], 1024)
        self.assertEqual(config["vector_store"]["provider"], "milvus")
        self.assertEqual(config["vector_store"]["config"]["url"], "http://localhost:19530")
        self.assertNotIn("embedding_dims", config["embedder"]["config"])
        with self.assertRaises(ValueError):
            build_config(settings, {})


if __name__ == "__main__":
    unittest.main()
