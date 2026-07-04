<?php
header('Content-Type: application/json; charset=utf-8');
$dir = __DIR__ . '/data';
if (!is_dir($dir)) @mkdir($dir, 0755, true);
$f = $dir . '/gantt_data.json';
function loadData($f){ if(!is_file($f)) return array('products'=>array()); $j=json_decode(file_get_contents($f), true); return is_array($j)?$j:array('products'=>array()); }
function dedupLaunches($products){ $best=array(); $order=array(); foreach($products as $p){ $nm=isset($p['name'])?trim(mb_strtolower($p['name'])):''; $tg=isset($p['tg'])?$p['tg']:''; $key=($tg==='')?('u'.uniqid('',true)):($nm.'|'.$tg); $sc=0; if(isset($p['ov'])&&is_array($p['ov'])){ foreach($p['ov'] as $ov){ if(isset($ov['status'])&&$ov['status']==='done') $sc++; } } if(!isset($best[$key])){ $best[$key]=array($sc,$p); $order[]=$key; } else if($sc>$best[$key][0]){ $best[$key]=array($sc,$p); } } $out=array(); foreach($order as $k){ $out[]=$best[$k][1]; } return $out; }
function stripDemo($products){ return array_values(array_filter($products, function($p){ $id=isset($p['id'])?$p['id']:''; $nm=isset($p['name'])?$p['name']:''; return $id!=='demo-lamp' && mb_stripos($nm,'пример')===false; })); }
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
$data['products'] = dedupLaunches(stripDemo($data['products']));
file_put_contents($f, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), LOCK_EX);
echo json_encode(array('ok'=>true,'count'=>count($data['products'])));
