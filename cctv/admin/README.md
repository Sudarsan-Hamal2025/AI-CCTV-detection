Admin dashboard (demo)

1. Place this project in your XAMPP `htdocs` folder (already here: `/cctv`).
2. Run the Python detection system to generate `events.db` and save images into `uploads/images/`:

```bash
python main.py
```

3. Open the dashboard in your browser:

```
http://localhost/cctv/admin/index.php
```

Notes:
- The dashboard reads `events.db` (SQLite) by default. To use MySQL instead, set these environment variables in your Apache/PHP environment: `CCTV_DB_HOST`, `CCTV_DB_USER`, `CCTV_DB_PASS`, `CCTV_DB_NAME`.
- A simple MySQL migration is provided at `db/init.sql`.
- The demo uses images saved under `uploads/images/` by `main.py`.
- You can define multiple cameras in `config.yaml` using the `cameras:` list, with each camera carrying `id`, `name`, `location`, and `source`.
- When you click an event, the dashboard shows the screenshot, alert message, camera name/location, and live feed from the detected camera.
- Live video is served from the Python backend at `http://localhost:8000/api/camera/feed?camera_id=CAM_ID`.
