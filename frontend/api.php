<?php
// header('Content-Type: application/json');
// header('Access-Control-Allow-Origin: *');
// header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
// header('Access-Control-Allow-Headers: Content-Type');

// Database configuration
$host = 'localhost';
$dbname = 'google_maps_data';
$username = 'root';
$password = 'ponnarukannan';



try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch(PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database connection failed']);
    exit;
}

$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if ($method === 'GET' && strpos($path, '/api/places') !== false) {
    try {
        // Fetch places with their categories
        $stmt = $pdo->prepare("
            SELECT 
                p.id,
                p.name,
                p.address,
                p.phone,
                p.rating,
                p.review_count,
                p.scraped_at,
                p.latitude,
                p.longitude,
                GROUP_CONCAT(c.name) as categories
            FROM places p
            LEFT JOIN place_categories pc ON p.id = pc.place_id
            LEFT JOIN categories c ON pc.category_id = c.id
            GROUP BY p.id
            ORDER BY p.scraped_at DESC
        ");
        $stmt->execute();
        $places = $stmt->fetchAll(PDO::FETCH_ASSOC);

        // Process categories
        foreach ($places as &$place) {
            $place['categories'] = $place['categories'] ? explode(',', $place['categories']) : [];
        }

        // Fetch all categories
        $stmt = $pdo->prepare("SELECT DISTINCT name FROM categories ORDER BY name");
        $stmt->execute();
        $categories = $stmt->fetchAll(PDO::FETCH_COLUMN);

        echo json_encode([
            'places' => $places,
            'categories' => $categories
        ]);

    } catch(PDOException $e) {
        http_response_code(500);
        echo json_encode(['error' => 'Failed to fetch data']);
    }
} else {
    http_response_code(404);
    echo json_encode(['error' => 'Endpoint not found']);
}
?>