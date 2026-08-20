<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CCTV Admin Dashboard - Demo</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="assets/styles.css" rel="stylesheet">
  </head>
  <body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container-fluid">
        <a class="navbar-brand" href="#">CCTV Admin (Demo)</a>
        <div class="ms-auto text-white">Status: <span id="statusBadge" class="badge bg-success">Running</span></div>
      </div>
    </nav>

    <div class="container my-4">
      <div class="row">
        <div class="col-lg-8 mb-4">
          <div class="card mb-4">
            <div class="card-header">Selected Alert</div>
            <div class="card-body">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <img id="liveImage" src="https://via.placeholder.com/640x480?text=No+Image" class="img-fluid border" style="width:100%; height:auto;" alt="Alert screenshot">
                </div>
                <div class="col-md-6">
                  <h5 id="alertTitle">No recent alerts</h5>
                  <p class="text-muted" id="alertMeta">Select an event to see details.</p>
                  <div class="mb-3">
                    <strong>Camera:</strong> <span id="alertCamera">N/A</span><br>
                    <strong>Location:</strong> <span id="alertLocation">N/A</span><br>
                    <strong>Time:</strong> <span id="alertTime">N/A</span>
                  </div>
                  <div class="alert alert-secondary" role="alert" id="alertDetails">No event message available.</div>
                </div>
              </div>
            </div>
          </div>

          <div class="card">
            <div class="card-header">Live Feed</div>
            <div class="card-body text-center">
              <img id="cameraFeed" src="https://via.placeholder.com/640x480?text=Select+an+event+to+view+live+feed" class="img-fluid border" style="width:100%; height:auto;" alt="Live camera feed">
              <p class="mt-2 text-muted" id="feedInfo">Live feed will appear here after selecting a camera event.</p>
            </div>
          </div>
        </div>
        <div class="col-lg-4">
          <div class="card">
            <div class="card-header">Recent Events</div>
            <div class="card-body" id="eventsList">
              Loading...
            </div>
          </div>
        </div>
      </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="assets/app.js"></script>
  </body>
</html>
