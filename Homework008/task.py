from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
import os
from requests import get, put
import urllib.parse
import json
import re

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        def isFileUploaded(fname):
            return fname in uploaded_files

        def fname2html(fname):
            style = "background:rgba(0, 200, 0, 0.25)" if isFileUploaded(fname) else ""
            return f"""
                <li style='{style}' onclick="fetch('/upload', {{'method': 'POST', 'body': '{fname}'}})">
                    {fname}
                </li>
            """


        def cleanDiskPath(path):
            if path.startswith("disk:/"):
                return path[len("disk:/"):]

        def load_files_in_dir(path, limit=5):
            offset = 0

            while True:
                fields = "_embedded.items.type,_embedded.items.path"
                resp = get(f"https://cloud-api.yandex.net/v1/disk/resources?path={path}&fields={fields}&limit={limit}&offset={offset}",
                    headers={"Authorization": "OAuth " + authKey})
                if not resp.content or resp.status_code >= 400:
                    print(resp.text)
                    break

                try:
                    payload = resp.json() if resp.content else None

                    for item in payload["_embedded"]["items"]:
                        offset += 1
                        if item["type"] != "dir":
                            uploaded_files.append(cleanDiskPath(item["path"])[len("Backup/"):])
                    
                    if len(payload["_embedded"]["items"]) < limit:
                        break
                except:
                    print(resp.text)
                    break

        uploaded_files = []
        load_files_in_dir("Backup")
        print(uploaded_files)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("""
            <html>
                <head>
                </head>
                <body>
                    <ul>
                      {files}
                    </ul>
                </body>
            </html>
        """.format(files="\n".join(map(fname2html, os.listdir("pdfs")))).encode())

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length'))
        fname = self.rfile.read(content_len).decode("utf-8")
        local_path = f"pdfs/{fname}"
        ya_path = f"Backup/{urllib.parse.quote(fname)}"
        
        resp = get(f"https://cloud-api.yandex.net/v1/disk/resources/upload?path={ya_path}",
                   headers={"Authorization": "OAuth " + authKey})

        print(resp.text)
        upload_url = json.loads(resp.text)["href"]
        print(upload_url)
        resp = put(upload_url, files={'file': (fname, open(local_path, 'rb'))})
        print(resp.status_code)
        self.send_response(200)
        self.end_headers()

def run(handler_class=BaseHTTPRequestHandler):
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

try:
    with open("auth_key.txt", 'r') as f:
        authKey = f.read()
except FileNotFoundError:
    print("No authentication key was loaded!")

run(handler_class=HttpHandler)