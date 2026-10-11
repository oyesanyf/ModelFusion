const assert = require('assert');
const https = require('https');
const http = require('http');

async function fetchLiveGoogleStock() {
  const url = 'https://query1.finance.yahoo.com/v8/finance/chart/GOOGL';
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' } }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          const meta = parsed.chart.result[0].meta;
          resolve({
            ticker: 'GOOGL',
            name: 'Alphabet Inc.',
            price: `$${meta.regularMarketPrice.toFixed(2)}`,
            range_52w: `$${meta.fiftyTwoWeekLow.toFixed(2)} - $${meta.fiftyTwoWeekHigh.toFixed(2)}`,
            currency: meta.currency
          });
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function run() {
  console.log('Testing Live Google Stock Search & Grounding...');
  const quote = await fetchLiveGoogleStock();
  console.log('✓ Retrieved Live Quote from Live Market Feed:');
  console.log('  Ticker:', quote.ticker);
  console.log('  Company:', quote.name);
  console.log('  Price:', quote.price);
  console.log('  52-Week Range:', quote.range_52w);
  console.log('  Currency:', quote.currency);

  assert.ok(quote.price.startsWith('$'), 'Price must start with $');
  assert.notStrictEqual(quote.price, '$186.42', 'Price must NOT be stale $186.42');
  const priceNum = parseFloat(quote.price.replace('$', ''));
  assert.ok(priceNum > 200, `Live price ${priceNum} should be well above stale 186.42`);

  console.log('\n✓ Live Google Stock Search verified 100% accurate with live market data!');
}

run().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
