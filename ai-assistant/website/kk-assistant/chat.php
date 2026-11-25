<?php
/**
 * Kickoff Kits "Kit Assistant" – server-side LLM endpoint (Groq API, function calling).
 * The browser widget posts {message} here; the API key never leaves the server.
 * Tools run on TEST DATA. Cart, discount and order actions are SIMULATED.
 */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
session_name('KKASSIST');
session_start();

$cfg = require __DIR__ . '/config.php';

$PRODUCTS = [
    ['id' => 1, 'name' => 'Home Jersey – Red #10', 'category' => 'Club Jerseys', 'colour' => 'red', 'price' => 49.99, 'stock' => ['S' => 4, 'M' => 0, 'L' => 7, 'XL' => 3]],
    ['id' => 2, 'name' => 'Away Jersey – White #7', 'category' => 'Club Jerseys', 'colour' => 'white', 'price' => 44.99, 'stock' => ['S' => 2, 'M' => 6, 'L' => 5, 'XL' => 0]],
    ['id' => 3, 'name' => 'Retro Lithuania Jersey – Yellow/Green #9', 'category' => 'Retro Jerseys', 'colour' => 'yellow/green', 'price' => 54.99, 'stock' => ['S' => 1, 'M' => 3, 'L' => 2, 'XL' => 4]],
    ['id' => 4, 'name' => 'Goalkeeper Jersey – Green #1', 'category' => 'Goalkeeper Jerseys', 'colour' => 'green', 'price' => 39.99, 'stock' => ['S' => 0, 'M' => 2, 'L' => 3, 'XL' => 1]],
];
$ORDERS = [
    ['ref' => 'KK-1001', 'email' => 'test.buyer@example.com', 'status' => 'Shipped – DPD tracking LT-TEST-55821, expected 26 Nov', 'items' => 'Away Jersey – White #7 (M)'],
    ['ref' => 'KK-1002', 'email' => 'jonas.test@example.com', 'status' => 'Processing – packing today', 'items' => 'Retro Lithuania Jersey #9 (L)'],
];
$DISCOUNTS = ['KICKOFF10' => ['percent' => 10, 'note' => 'Newsletter welcome code, first order only']];

$SYSTEM = 'You are "Kit Assistant", the customer service and shopping assistant of Kickoff Kits, a small online football jersey shop in Šiauliai, Lithuania (a PrestaShop store). This is a TEST ENVIRONMENT: cart, discount and order actions are simulated and use test data.
Rules:
- Use the tools for product, stock, order and discount facts. Never invent products, prices, stock or order details.
- The shop sells ONLY the products returned by search_products (4 Kickoff Kits jerseys). Never mention any other team, brand or product.
- Before adding anything to the cart you need the product and the size (S, M, L or XL). If the customer is vague (no product type, size or budget), FIRST call search_products with no filters, THEN ask ONE short clarifying question offering those real products (name and price) and asking for the size. Do not call add_to_cart until the details are clear.
- If a size is out of stock, say so and suggest available sizes or a similar jersey.
- Order lookups need BOTH the order reference and the email used for the order; get_order_status checks that they match. Never reveal another customer\'s email, address or order details.
- You may only apply a discount code the customer gives you and the tool confirms. You cannot create, invent or increase discounts.
- You cannot issue refunds, cancel orders, change prices or use admin functions. Refuse politely and point to support@kickoffkits.test.
- When you perform a simulated action, say that it was simulated in this test shop.
- Be friendly and brief: at most 5 short sentences, prices in EUR (e.g. €44.99). Plain text, no markdown tables.';

$TOOLS = [
    ['type' => 'function', 'function' => ['name' => 'search_products', 'description' => 'Search the Kickoff Kits catalogue. Returns products with id, name, category, colour, price (EUR) and sizes in stock. Call with no filters to list everything.',
        'parameters' => ['type' => 'object', 'properties' => ['query' => ['type' => ['string', 'null']], 'max_price' => ['type' => ['number', 'null']], 'size' => ['type' => ['string', 'null'], 'description' => 'S, M, L or XL']]]]],
    ['type' => 'function', 'function' => ['name' => 'check_stock', 'description' => 'Check how many units of one product are in stock in one size.',
        'parameters' => ['type' => 'object', 'properties' => ['product_id' => ['type' => 'integer'], 'size' => ['type' => 'string', 'enum' => ['S', 'M', 'L', 'XL']]], 'required' => ['product_id', 'size']]]],
    ['type' => 'function', 'function' => ['name' => 'add_to_cart', 'description' => 'SIMULATED: add a product in a size to the customer\'s cart in this test shop. Only call when product and size are clear and in stock.',
        'parameters' => ['type' => 'object', 'properties' => ['product_id' => ['type' => 'integer'], 'size' => ['type' => 'string', 'enum' => ['S', 'M', 'L', 'XL']], 'quantity' => ['type' => ['integer', 'null']]], 'required' => ['product_id', 'size']]]],
    ['type' => 'function', 'function' => ['name' => 'apply_discount', 'description' => 'SIMULATED: validate a discount code the customer gave and apply it to the cart. Cannot create new codes.',
        'parameters' => ['type' => 'object', 'properties' => ['code' => ['type' => 'string']], 'required' => ['code']]]],
    ['type' => 'function', 'function' => ['name' => 'get_order_status', 'description' => 'Look up an order\'s status. Requires the order reference AND the email used for that order; refuses if they do not match (privacy).',
        'parameters' => ['type' => 'object', 'properties' => ['order_ref' => ['type' => 'string'], 'email' => ['type' => 'string']], 'required' => ['order_ref', 'email']]]],
];

function out($data, $code = 200) { http_response_code($code); echo json_encode($data, JSON_UNESCAPED_UNICODE); exit; }

$in = json_decode(file_get_contents('php://input') ?: '{}', true) ?: [];
if (!empty($in['reset'])) { $_SESSION = []; out(['ok' => true]); }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(['ok' => true, 'service' => 'Kit Assistant', 'model' => $cfg['model']]);
$msg = trim(mb_substr((string)($in['message'] ?? ''), 0, 1500));
if ($msg === '') out(['error' => 'Empty message'], 400);

if (empty($_SESSION['messages'])) { $_SESSION['messages'] = [['role' => 'system', 'content' => $SYSTEM]]; $_SESSION['cart'] = []; $_SESSION['discount'] = null; }
$_SESSION['messages'][] = ['role' => 'user', 'content' => $msg];

function totals() {
    $sub = 0; foreach ($_SESSION['cart'] as $c) $sub += $c['price'] * $c['qty'];
    $off = $_SESSION['discount'] ? round($sub * $_SESSION['discount']['percent'] / 100, 2) : 0;
    return ['subtotal' => round($sub, 2), 'discount' => $off, 'total' => round($sub - $off, 2)];
}
function findProduct($id) { global $PRODUCTS; foreach ($PRODUCTS as $p) if ($p['id'] === (int)$id) return $p; return null; }

function runTool($name, $a) {
    global $PRODUCTS, $ORDERS, $DISCOUNTS;
    switch ($name) {
        case 'search_products':
            $words = array_values(array_filter(preg_split('/\s+/', mb_strtolower((string)($a['query'] ?? ''))), fn($w) => $w !== '' && !in_array($w, ['jersey', 'jerseys', 'shirt', 'kit'])));
            $txt = fn($p) => mb_strtolower($p['name'] . ' ' . $p['category'] . ' ' . $p['colour']);
            $res = array_filter($PRODUCTS, function ($p) use ($words, $txt) { foreach ($words as $w) if (mb_strpos($txt($p), $w) === false) return false; return true; });
            if (!$res && $words) $res = array_filter($PRODUCTS, function ($p) use ($words, $txt) { foreach ($words as $w) if (mb_strpos($txt($p), $w) !== false) return true; return false; });
            if (!empty($a['max_price'])) $res = array_filter($res, fn($p) => $p['price'] <= (float)$a['max_price']);
            if (!empty($a['size'])) { $s = strtoupper($a['size']); $res = array_filter($res, fn($p) => ($p['stock'][$s] ?? 0) > 0); }
            return ['read', array_values(array_map(fn($p) => ['id' => $p['id'], 'name' => $p['name'], 'category' => $p['category'], 'colour' => $p['colour'], 'price' => $p['price'], 'sizes_in_stock' => array_keys(array_filter($p['stock']))], $res))];
        case 'check_stock':
            $p = findProduct($a['product_id'] ?? 0); if (!$p) return ['denied', 'Error: Unknown product id'];
            $s = strtoupper((string)($a['size'] ?? '')); return ['read', ['product' => $p['name'], 'size' => $s, 'units' => $p['stock'][$s] ?? 0]];
        case 'add_to_cart':
            $p = findProduct($a['product_id'] ?? 0); if (!$p) return ['denied', 'Error: Unknown product id'];
            $s = strtoupper((string)($a['size'] ?? '')); $q = max(1, min(5, (int)($a['quantity'] ?? 1)));
            if (($p['stock'][$s] ?? 0) < $q) return ['denied', "Error: Only " . ($p['stock'][$s] ?? 0) . " left in size $s"];
            $_SESSION['cart'][] = ['name' => $p['name'], 'size' => $s, 'qty' => $q, 'price' => $p['price']];
            return ['simulated action', ['simulated' => true, 'cart' => array_map(fn($c) => "{$c['qty']} x {$c['name']} ({$c['size']})", $_SESSION['cart']), 'subtotal_eur' => totals()['subtotal']]];
        case 'apply_discount':
            $c = strtoupper(trim((string)($a['code'] ?? '')));
            if (!isset($DISCOUNTS[$c])) return ['denied', 'Error: Code not valid. Only existing codes can be applied; the assistant cannot create discounts.'];
            if (!$_SESSION['cart']) return ['denied', 'Error: Cart is empty – add a product first'];
            $_SESSION['discount'] = ['code' => $c, 'percent' => $DISCOUNTS[$c]['percent']];
            return ['simulated action', ['simulated' => true, 'valid' => true, 'code' => $c, 'percent' => $DISCOUNTS[$c]['percent'], 'total_eur' => totals()['total']]];
        case 'get_order_status':
            foreach ($ORDERS as $o) if (strcasecmp($o['ref'], trim((string)($a['order_ref'] ?? ''))) === 0 && strcasecmp($o['email'], trim((string)($a['email'] ?? ''))) === 0)
                return ['read', ['order' => $o['ref'], 'status' => $o['status'], 'items' => $o['items']]];
            return ['denied', 'Error: Access denied: order reference and email do not match. Do not reveal any order data.'];
    }
    return ['denied', "Error: Unknown tool $name"];
}

function groq($body, $cfg) {
    for ($i = 0; $i < 3; $i++) {
        $ch = curl_init('https://api.groq.com/openai/v1/chat/completions');
        curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 60,
            CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $cfg['key'], 'Content-Type: application/json'],
            CURLOPT_POSTFIELDS => json_encode($body, JSON_UNESCAPED_UNICODE)]);
        $res = curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); $err = curl_error($ch); curl_close($ch);
        if ($code === 429 && $i < 2) { sleep(6 * ($i + 1)); continue; }
        if ($res === false) throw new Exception("Connection error: $err");
        $j = json_decode($res, true);
        if ($code !== 200) throw new Exception('LLM API error ' . $code . ': ' . substr($j['error']['message'] ?? $res, 0, 200));
        return $j;
    }
    throw new Exception('The AI is busy (rate limit). Please try again in a few seconds.');
}

$calls = [];
try {
    for ($round = 0; $round < 6; $round++) {
        $j = groq(['model' => $cfg['model'], 'messages' => $_SESSION['messages'], 'tools' => $TOOLS, 'tool_choice' => 'auto', 'temperature' => 0.2], $cfg);
        $m = $j['choices'][0]['message'];
        $tcs = $m['tool_calls'] ?? [];
        $entry = ['role' => 'assistant', 'content' => $m['content'] ?? ''];
        if ($tcs) $entry['tool_calls'] = $tcs;
        $_SESSION['messages'][] = $entry;
        if (!$tcs) {
            if (count($_SESSION['messages']) > 40) $_SESSION['messages'] = array_merge([$_SESSION['messages'][0]], array_slice($_SESSION['messages'], -30));
            out(['reply' => $m['content'] ?? '', 'tool_calls' => $calls, 'cart' => $_SESSION['cart'], 'discount' => $_SESSION['discount'], 'totals' => totals()]);
        }
        foreach ($tcs as $tc) {
            $args = json_decode($tc['function']['arguments'] ?? '{}', true) ?: [];
            [$kind, $res] = runTool($tc['function']['name'], $args);
            $calls[] = ['time' => date('H:i:s'), 'tool' => $tc['function']['name'], 'kind' => $kind, 'input' => $args, 'output' => $res];
            $_SESSION['messages'][] = ['role' => 'tool', 'tool_call_id' => $tc['id'], 'content' => json_encode($res, JSON_UNESCAPED_UNICODE)];
        }
    }
    out(['reply' => 'Sorry, I could not finish that request.', 'tool_calls' => $calls, 'cart' => $_SESSION['cart'], 'discount' => $_SESSION['discount'], 'totals' => totals()]);
} catch (Exception $e) {
    array_pop($_SESSION['messages']);
    out(['error' => $e->getMessage(), 'tool_calls' => $calls], 502);
}
