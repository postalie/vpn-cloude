<?php
/**
 * VPN Subscription Proxy Script
 * Handles device limit tracking and redirects to the original subscription.
 */

// Configuration
$RAILWAY_API_URL = "https://vpn-cloudee-production.up.railway.app"; // Update if different
$API_SECRET = "CloudeVpnVOIDAPI_1488";
$JSON_FILE = "devices.json";
$REDIRECT_BASE = "https://cloudevpn.cfd/sub/"; // Base URL for actual subscription

// 1. Get Subscription ID
$id = isset($_GET['id']) ? $_GET['id'] : null;

if (!$id) {
    die("Error: No ID provided.");
}

// 2. Determine Unique Device Hash
$ip = $_SERVER['REMOTE_ADDR'];
$ua = isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : "unknown";
$device_hash = md5($ip . $ua);

// 3. Load or Create JSON Data
$data = [];
if (file_exists($JSON_FILE)) {
    $data = json_decode(file_get_contents($JSON_FILE), true);
}

// 4. Check if device is already known
if (isset($data[$id]) && in_array($device_hash, $data[$id])) {
    // Already registered, just redirect
    header("Location: " . $REDIRECT_BASE . $id);
    exit;
}

// 5. New Device: Verify with Railway API
$ch = curl_init($RAILWAY_API_URL . "/api/register_device");
$payload = json_encode([
    "uuid" => $id,
    "hash" => $device_hash
]);

curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'X-API-Key: ' . $API_SECRET
]);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 5);

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($http_code == 200) {
    $res_data = json_decode($response, true);
    
    if (isset($res_data['status']) && $res_data['status'] === 'ok') {
        // Register locally and redirect
        if (!isset($data[$id])) {
            $data[$id] = [];
        }
        $data[$id][] = $device_hash;
        file_put_contents($JSON_FILE, json_encode($data));
        
        header("Location: " . $REDIRECT_BASE . $id);
        exit;
    } elseif (isset($res_data['status']) && $res_data['status'] === 'limit_exceeded') {
        // Limit reached: Show warning as a fake VPN config
        header("Content-Type: text/plain; charset=utf-8");
        // We return a base64 encoded warning message as a single key
        $warning = "внимание превышен лимит устройств, удалите устройства, либо сбросьте ссылку в меню";
        echo base64_encode($warning);
        exit;
    }
}

// Fallback or Error
header("Content-Type: text/plain; charset=utf-8");
echo base64_encode("❌ Ошибка проверки лимита. Попробуйте обновить ссылку в боте.");
?>
