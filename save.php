<?php
header('Content-Type: application/json; charset=utf-8');
$dir = __DIR__ . '/data';
if (!is_dir($dir)) @mkdir($dir, 0755, true);
$f = $dir . '/gantt_data.json';
function loadData($f){ if(!is_file($f)) return array('products'=>array()); $j=json_decode(file_get_contents($f), true); return is_array($j)?$j:array('products'=>array()); }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { echo json_encode(array('ok'=>false,'err'=>'use POST')); exit; }
$in = json_decode(file_get_contents('php://input'), true);
if (!is_array($in)) { http_response_code(400); echo json_encode(array('ok'=>false,'err'=>'bad json')); exit; }
$data = loadData($f);
if (!isset($data['products']) || !is_array($data['products'])) $data['products']=array();
$op = isset($in['op']) ? $in['op'] : 'merge';
if ($op==='delete' && isset($in['id'])) {
  $data['products'] = array_values(array_filter($data['products'], function($p) use($in){ return (isset($p['id']) ? $p['id'] : '') !== $in['id']; }));
} else if ($op==='replace' && isset($in['products'])) {
  $data['products'] = $in['products'];
} else if (isset($in['products']) && is_array($in['products'])) {
  $byId = array();
  foreach ($data['products'] as $p) { $k = isset($p['id'])?$p['id']:uniqid(); $byId[$k]=$p; }
  foreach ($in['products'] as $p) { if (isset($p['id'])) $byId[$p['id']]=$p; }
  $data['products'] = array_values($byId);
} else { http_response_code(400); echo json_encode(array('ok'=>false,'err'=>'no products')); exit; }
file_put_contents($f, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), LOCK_EX);
echo json_encode(array('ok'=>true,'count'=>count($data['products'])));
