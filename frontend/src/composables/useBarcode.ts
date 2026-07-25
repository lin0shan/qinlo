/**
 * 前端条码渲染 + 打印
 *
 * 使用 JsBarcode 在 Canvas 上绘制 Code128 条码，
 * 通过新窗口 + window.print() 实现打印。
 */

import JsBarcode from 'jsbarcode'

/**
 * 在指定 Canvas 上绘制 Code128 条码
 * @param element Canvas 元素或选择器
 * @param code 条码内容
 * @returns 是否渲染成功
 */
function render(element: string | HTMLCanvasElement, code: string): boolean {
  try {
    JsBarcode(element, code, {
      format: 'CODE128',
      displayValue: true,
      fontSize: 14,
      height: 60,
      margin: 10,
      background: '#ffffff',
      lineColor: '#000000',
    })
    return true
  } catch {
    return false
  }
}

/**
 * 打印条码标签
 * 打开新窗口渲染条码 + 商品名，自动触发打印
 * @param code 条码内容
 * @param name 商品名称
 */
function print(code: string, name: string) {
  const escapedName = name.replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const escapedCode = code.replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>条码打印</title>
<style>
  @page { size: 50mm 30mm; margin: 2mm; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { text-align:center; padding:30px 20px; font-family:-apple-system,sans-serif; }
  .name { font-size:14px; font-weight:600; margin-bottom:6px; color:#333; }
  .code { font-size:11px; color:#888; margin-top:6px; letter-spacing:1px; }
  @media print {
    body { padding:0; }
    .name { font-size:12px; }
    .code { font-size:10px; }
  }
</style></head><body>
  <div class="name">${escapedName}</div>
  <svg id="bc"></svg>
  <div class="code">${escapedCode}</div>
  <script>
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js';
    script.onload = function() {
      JsBarcode('#bc', '${escapedCode}', {
        format:'CODE128', displayValue:false, height:40, margin:2,
        background:'#ffffff', lineColor:'#000000'
      });
      setTimeout(function() { window.print(); }, 600);
    };
    document.head.appendChild(script);
  <\/script>
</body></html>`

  const w = window.open('', '_blank', 'width=420,height=360')
  if (w) {
    w.document.write(html)
    w.document.close()
  }
}

export function useBarcode() {
  return { render, print }
}
