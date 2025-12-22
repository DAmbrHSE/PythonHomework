from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import json

class DatabaseManager:
    def database_update(file_name, data):
        try:
            with open(file_name, 'w') as f:
                f.write(json.dumps(data))
        except:
            print("Problem with writing into the file")

    def database_load(file_name):
        data = {}

        try:
            with open(file_name, 'r') as f:
                data = json.load(f)
            print("Database loaded from file.")
            print("Elements count:", len(data))
        except json.JSONDecodeError:
            print("Database file is corrupted")
        except FileNotFoundError:
            print("Database file not found")

        return data

class TaskManager:
    tasks = {}
    next_id = -1
    db_file_name = "tasks.txt"

    def list_tasks(self):
        return [self.tasks[id] for id in self.tasks]

    def add_new_task(self, title, priority):
        id = self.next_id
        self.next_id += 1

        self.tasks[id] = { "title" : title, "id" : id, "priority" : priority, "isDone" : False }
        DatabaseManager.database_update(self.db_file_name, self.list_tasks())
        return self.tasks[id]
    
    def mark_task_complete(self, id):
        self.tasks[id]["isDone"] = True
        DatabaseManager.database_update(self.db_file_name, self.list_tasks())

    def __init__(self):
        db_tasks = DatabaseManager.database_load(self.db_file_name)
        self.tasks = {task["id"] : task  for task in db_tasks}
        self.next_id = max(self.tasks) + 1 if len(db_tasks) > 0 else 0 # max - среди ключей
        print("Next ID:", self.next_id)

TASK_MANAGER = TaskManager()

class SimpleJSONServerHandler(BaseHTTPRequestHandler):
    def read_json_body(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return None
        try:
            return json.loads(raw)
        except:
            return None
    
    def send_json(self, data, status):
        data_string = json.dumps(data).encode("utf-8") if (data != None) else b""
        data_size = len(data_string)

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(data_size))
        self.end_headers()
        self.wfile.write(data_string)

    def send_error(self, status, msg):
        self.send_json({"error": msg}, status)

class TaskManagerServerHandler(SimpleJSONServerHandler):
    def list_tasks(self):
        self.send_json(TASK_MANAGER.list_tasks(), 200)

    def add_new_task(self):
        in_data = self.read_json_body()
        
        if not in_data or "title" not in in_data or "priority" not in in_data:
            return self.send_error(400, "Fields 'title' and 'priority' are required")

        task = TASK_MANAGER.add_new_task(in_data["title"], in_data["priority"])
        self.send_json(task, 201)

    def mark_task_complete(self, id):
        try:
            TASK_MANAGER.mark_task_complete(int(id))
            self.send_json(None, 200)
        except KeyError or ValueError:
            self.send_error(404, "Not found")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/tasks":
            self.list_tasks()
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]

        if parsed.path == "/tasks":
            self.add_new_task()
        elif len(parts) == 3 and parts[0] == 'tasks' and parts[2] == 'complete':
            self.mark_task_complete(parts[1])
        else:
            self.send_error(404, "Not found")


def run(host="127.0.0.1", port=8000):
    server = HTTPServer((host, port), TaskManagerServerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

run()
