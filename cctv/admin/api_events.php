<?php
header('Content-Type: application/json; charset=utf-8');
require_once __DIR__ . '/db.php';

$pdo = get_db();

function get_table_columns($pdo, $table) {
    $stmt = $pdo->query("PRAGMA table_info($table)");
    $columns = [];
    foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
        $columns[] = $row['name'];
    }
    return $columns;
}

// Read most recent events
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
try {
    $columns = ['id', 'timestamp', 'event_type', 'details', 'image_path'];
    $tableColumns = get_table_columns($pdo, 'events');
    foreach (['camera_id', 'camera_name', 'camera_location'] as $col) {
        if (in_array($col, $tableColumns, true)) {
            $columns[] = $col;
        }
    }
    $select = implode(', ', $columns);
    $stmt = $pdo->prepare("SELECT $select FROM events ORDER BY timestamp DESC LIMIT :limit");
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->execute();
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $events = [];
    foreach ($rows as $r) {
        $img = $r['image_path'];
        if ($img && $img !== '') {
            // Convert to web-accessible URL relative to admin folder
            $image_url = '..' . '/' . ltrim($img, '/\\');
        } else {
            $image_url = null;
        }
        $events[] = [
            'id' => $r['id'],
            'timestamp' => $r['timestamp'],
            'event_type' => $r['event_type'],
            'details' => $r['details'],
            'image_url' => $image_url,
            'camera_id' => $r['camera_id'] ?? null,
            'camera_name' => $r['camera_name'] ?? null,
            'camera_location' => $r['camera_location'] ?? null,
        ];
    }
    echo json_encode(['ok' => true, 'events' => $events]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
}

?>
