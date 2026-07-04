<?php
header('Content-Type: application/json; charset=utf-8');
$dir = __DIR__ . '/data'; if (!is_dir($dir)) @mkdir($dir, 0755, true);
$f = $dir . '/gantt_config.json';
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { echo json_encode(array('ok'=>false,'err'=>'use POST')); exit; }
$in = json_decode(file_get_contents('php://input'), true);
if (!is_array($in) || !isset($in['stages']) || !is_array($in['stages'])) { http_response_code(400); echo json_encode(array('ok'=>false,'err'=>'bad config')); exit; }
file_put_contents($f, json_encode($in, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), LOCK_EX);
echo json_encode(array('ok'=>true,'stages'=>count($in['stages'])));
