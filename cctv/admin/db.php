<?php
// Simple DB helper: supports SQLite (default) or MySQL if env provided
function get_db() {
    // Prefer environment variables for MySQL (optional)
    $mysql_host = getenv('CCTV_DB_HOST');
    if ($mysql_host && $mysql_host !== '') {
        $user = getenv('CCTV_DB_USER') ?: 'root';
        $pass = getenv('CCTV_DB_PASS') ?: '';
        $name = getenv('CCTV_DB_NAME') ?: 'cctv_security';
        try {
            $dsn = "mysql:host=$mysql_host;dbname=$name;charset=utf8mb4";
            $pdo = new PDO($dsn, $user, $pass, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
            return $pdo;
        } catch (Exception $e) {
            http_response_code(500);
            echo json_encode(['error' => 'MySQL connection failed: ' . $e->getMessage()]);
            exit;
        }
    }

    // Fallback to SQLite (default for this demo)
    $db_path = __DIR__ . '/../events.db';
    if (!file_exists($db_path)) {
        // return empty DB connection (in-memory) to avoid PHP warnings
        $pdo = new PDO('sqlite::memory:');
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        return $pdo;
    }

    try {
        $pdo = new PDO('sqlite:' . $db_path);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        return $pdo;
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode(['error' => 'SQLite connection failed: ' . $e->getMessage()]);
        exit;
    }
}

?>
