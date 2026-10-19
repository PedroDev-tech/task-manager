import os
import tempfile
import unittest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app import app, db, Task  # noqa: E402


def tearDownModule():
    if os.path.exists(_db_path):
        os.unlink(_db_path)


class TaskManagerTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def create_task(self, **kwargs):
        data = {"title": "Estudar", "priority": "media", "status": "pendente"}
        data.update(kwargs)
        return self.client.post("/create", data=data, follow_redirects=True)

    def test_home_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Task Manager", response.get_data(as_text=True))

    def test_create_and_list(self):
        self.create_task(title="Comprar leite")
        response = self.client.get("/tasks")
        self.assertIn("Comprar leite", response.get_data(as_text=True))

    def test_create_requires_title(self):
        self.client.post("/create", data={"title": ""}, follow_redirects=True)
        with app.app_context():
            self.assertEqual(Task.query.count(), 0)

    def test_invalid_date_is_rejected(self):
        self.client.post(
            "/create",
            data={"title": "Tarefa", "due_date": "2020-13-99"},
            follow_redirects=True,
        )
        with app.app_context():
            self.assertEqual(Task.query.count(), 0)

    def test_edit_updates_task(self):
        self.create_task(title="Antigo")
        with app.app_context():
            task_id = Task.query.first().id
        self.client.post(
            f"/edit/{task_id}",
            data={"title": "Novo", "priority": "alta", "status": "pendente"},
            follow_redirects=True,
        )
        with app.app_context():
            task = db.session.get(Task, task_id)
            self.assertEqual(task.title, "Novo")
            self.assertEqual(task.priority, "alta")

    def test_toggle_status(self):
        self.create_task(title="Alternar")
        with app.app_context():
            task_id = Task.query.first().id
        self.client.post(f"/toggle/{task_id}", follow_redirects=True)
        with app.app_context():
            self.assertEqual(db.session.get(Task, task_id).status, "concluida")

    def test_delete_task(self):
        self.create_task(title="Remover")
        with app.app_context():
            task_id = Task.query.first().id
        self.client.post(f"/delete/{task_id}", follow_redirects=True)
        with app.app_context():
            self.assertIsNone(db.session.get(Task, task_id))

    def test_status_filter(self):
        self.create_task(title="PendenteX", status="pendente")
        self.create_task(title="ConcluidaX", status="concluida")
        html = self.client.get("/tasks?status=pendentes").get_data(as_text=True)
        self.assertIn("PendenteX", html)
        self.assertNotIn("ConcluidaX", html)

    def test_pagination(self):
        for i in range(10):
            self.create_task(title=f"Tarefa {i}")
        html = self.client.get("/tasks").get_data(as_text=True)
        self.assertIn("page=2", html)

    def test_language_switch(self):
        en = self.client.get("/?lang=en").get_data(as_text=True)
        self.assertIn("Organize your day with clarity", en)
        pt = self.client.get("/?lang=pt").get_data(as_text=True)
        self.assertIn("Organize o seu dia", pt)

    def test_api_list_empty(self):
        response = self.client.get("/api/tasks")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"tasks": []})

    def test_api_crud(self):
        created = self.client.post("/api/tasks", json={"title": "Via API", "priority": "alta"})
        self.assertEqual(created.status_code, 201)
        payload = created.get_json()
        self.assertEqual(payload["title"], "Via API")
        task_id = payload["id"]

        fetched = self.client.get(f"/api/tasks/{task_id}")
        self.assertEqual(fetched.status_code, 200)

        updated = self.client.put(f"/api/tasks/{task_id}", json={"status": "concluida"})
        self.assertEqual(updated.get_json()["status"], "concluida")

        deleted = self.client.delete(f"/api/tasks/{task_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get(f"/api/tasks/{task_id}").status_code, 404)

    def test_api_create_requires_title(self):
        response = self.client.post("/api/tasks", json={})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
