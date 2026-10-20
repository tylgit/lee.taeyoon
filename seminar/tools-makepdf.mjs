import { chromium } from 'playwright';
const DIST = '/home/user/lee.taeyoon/seminar/dist/';
const OUT  = '/home/user/lee.taeyoon/seminar/pdf/';
const jobs = [
  ['textbook', '샬롬대학_AI교재1_처음만나는AI.pdf',      { format: 'A4', landscape: false }],
  ['book2',    '샬롬대학_AI교재2_무엇이새로운가.pdf',     { format: 'A4', landscape: false }],
  ['workbook', '샬롬대학_AI워크북_실습.pdf',             { format: 'A4', landscape: false }],
  ['slides',   '샬롬대학_AI슬라이드_발표용.pdf',          { format: 'A4', landscape: true  }],
];
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const [name, out, opt] of jobs) {
  const p = await b.newPage({ viewport: { width: 1280, height: 900 }, colorScheme: 'light' });
  await p.goto('file://' + DIST + name + '.html', { waitUntil: 'networkidle' });
  await p.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));
  await p.emulateMedia({ media: 'print' });
  await p.waitForTimeout(700);
  await p.pdf({
    path: OUT + out, printBackground: true, preferCSSPageSize: false,
    margin: opt.landscape ? { top:'0', right:'0', bottom:'0', left:'0' }
                          : { top:'16mm', right:'14mm', bottom:'16mm', left:'14mm' },
    ...opt,
  });
  console.log('완료:', out);
  await p.close();
}
await b.close();
