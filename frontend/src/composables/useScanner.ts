/**
 * Barcode scanner composable.
 *
 * USB scanner: global keydown listener; character interval < 100ms is treated as
 *              scanner input; Enter triggers callback and clears the buffer.
 * Phone camera: uses @undecaf/zbar-wasm (WebAssembly ZBar),
 *              self-managed getUserMedia -> canvas -> decode pipeline;
 *              no dependency on BarcodeDetector / html5-qrcode / quagga2.
 */
import { scanImageData, type ZBarSymbol, type ZBarScanner, getDefaultScanner } from '@undecaf/zbar-wasm'

// --- USB scanner global state ---

let globalBuffer = ''
let globalLastKeyTime = 0
let globalListeners: Array<(barcode: string) => void> = []
let globalListening = false

const SCANNER_INTERVAL_MS = 100 // If character interval exceeds this, treat as manual input and clear buffer

function globalHandleKeyDown(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName || ''
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return

  if (e.key === 'Enter') {
    if (globalBuffer.length === 0) return
    e.preventDefault()
    const barcode = globalBuffer
    globalBuffer = ''
    globalLastKeyTime = 0
    for (const cb of globalListeners) {
      cb(barcode)
    }
    return
  }

  if (e.key.length !== 1 || e.ctrlKey || e.altKey || e.metaKey) return

  const now = Date.now()
  if (globalLastKeyTime > 0 && now - globalLastKeyTime > SCANNER_INTERVAL_MS) {
    globalBuffer = ''
  }

  globalBuffer += e.key
  globalLastKeyTime = now
}

// --- Camera scan global state ---

let cameraActive = false
let cameraStream: MediaStream | null = null
let cameraVideo: HTMLVideoElement | null = null
let scanLoopTimer: ReturnType<typeof setTimeout> | null = null
let cameraTimeout: ReturnType<typeof setTimeout> | null = null
let zbarScanner: ZBarScanner | null = null

// --- Public utilities ---

function playBeep() {
  try {
    const ctx = new AudioContext()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.value = 800
    osc.type = 'square'
    gain.gain.setValueAtTime(0.3, ctx.currentTime)
    osc.start()
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1)
    osc.stop(ctx.currentTime + 0.1)
  } catch {
    /* Ignore audio errors */
  }
}

function isValidStoreBarcode(code: string): boolean {
  return /^[A-Z]{2}\d{8}$/.test(code.trim().toUpperCase())
}

/**
 * Scan line CSS: overlays an animated horizontal scan line on the camera container.
 */
const SCAN_LINE_CSS = `
@keyframes scanner-line-move {
  0%   { top: 5%; }
  50%  { top: 90%; }
  100% { top: 5%; }
}
.scanner-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 2;
}
.scanner-line {
  position: absolute;
  left: 5%;
  width: 90%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #ee0a24, #ee0a24, transparent);
  box-shadow: 0 0 8px 2px rgba(238,10,36,0.5);
  animation: scanner-line-move 2s ease-in-out infinite;
}
.scanner-corners {
  position: absolute;
  inset: 8px;
  border: 2px solid rgba(255,255,255,0.4);
  border-radius: 8px;
}
.scanner-corners::before,
.scanner-corners::after {
  content: '';
  position: absolute;
  width: 24px;
  height: 24px;
}
.scanner-corners::before {
  top: -2px;
  left: -2px;
  border-top: 3px solid #ee0a24;
  border-left: 3px solid #ee0a24;
  border-radius: 4px 0 0 0;
}
.scanner-corners::after {
  bottom: -2px;
  right: -2px;
  border-bottom: 3px solid #ee0a24;
  border-right: 3px solid #ee0a24;
  border-radius: 0 0 4px 0;
}
`

// Inject scan line CSS (once only)
let scanLineCssInjected = false
function injectScanLineCss() {
  if (scanLineCssInjected) return
  scanLineCssInjected = true
  const style = document.createElement('style')
  style.textContent = SCAN_LINE_CSS
  document.head.appendChild(style)
}

// --- 导出 ---

export function useScanner() {
  let myCallback: ((barcode: string) => void) | null = null

  // ---- USB scanner ----

  function startScan(callback: (barcode: string) => void) {
    myCallback = callback
    globalListeners.push(callback)
    if (globalListening) return
    globalListening = true
    globalBuffer = ''
    globalLastKeyTime = 0
    window.addEventListener('keydown', globalHandleKeyDown)
  }

  function stopScan() {
    if (myCallback) {
      globalListeners = globalListeners.filter((cb) => cb !== myCallback)
      myCallback = null
    }
    if (globalListeners.length === 0 && globalListening) {
      globalListening = false
      window.removeEventListener('keydown', globalHandleKeyDown)
      globalBuffer = ''
      globalLastKeyTime = 0
    }
  }

  // ---- Camera scan (zbar-wasm) ----

  async function startCamera(elementId: string, onScanned: (barcode: string) => void): Promise<boolean> {
    await stopCamera()

    const container = document.getElementById(elementId)
    if (!container) {
      console.error('[useScanner] Container not found:', elementId)
      return false
    }

    try {
      // Inject scan line CSS
      injectScanLineCss()

      // Clear container
      container.innerHTML = ''

      // Get rear camera video stream
      // Try with focusMode constraint first (helps focusing); fall back to basic constraints if not supported
      let stream: MediaStream
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'environment',
            width: { ideal: 1280 },
            height: { ideal: 720 },
            // @ts-expect-error focusMode is a standard MediaTrackConstraints field, but TS types don't include it
            focusMode: 'continuous',
          },
          audio: false,
        })
      } catch (_constraintErr) {
        // Some browsers reject unknown constraints; fall back to basic params
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        })
      }
      cameraStream = stream

      // Create video element
      const video = document.createElement('video')
      video.setAttribute('autoplay', '')
      video.setAttribute('playsinline', '')
      video.setAttribute('muted', '')
      video.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block;'
      video.srcObject = stream
      container.appendChild(video)
      cameraVideo = video

      // Add scan animation overlay
      const overlay = document.createElement('div')
      overlay.className = 'scanner-overlay'
      overlay.innerHTML = '<div class="scanner-corners"></div><div class="scanner-line"></div>'
      container.style.position = 'relative'
      container.appendChild(overlay)

      await video.play()

      // Wait for first video frame
      await new Promise<void>((resolve) => {
        if (video.readyState >= 2) {
          resolve()
        } else {
          video.addEventListener('loadeddata', () => resolve(), { once: true })
        }
      })

      // Create off-screen canvas for frame capture
      const captureCanvas = document.createElement('canvas')
      const captureCtx = captureCanvas.getContext('2d', { willReadFrequently: true })
      if (!captureCtx) {
        throw new Error('Cannot create canvas 2d context')
      }

      // Get zbar scanner instance (reused to avoid re-initializing WASM every time)
      if (!zbarScanner) {
        zbarScanner = await getDefaultScanner()
      }

      cameraActive = true

      // Scan loop: grab a frame from video every 150ms and feed to zbar for decoding
      const scanFrame = async () => {
        if (!cameraActive || !cameraVideo || cameraVideo.paused || cameraVideo.ended) {
          return
        }

        const vw = cameraVideo.videoWidth
        const vh = cameraVideo.videoHeight
        if (vw === 0 || vh === 0) {
          // Video frame not ready yet, keep waiting
          scanLoopTimer = setTimeout(scanFrame, 150)
          return
        }

        try {
          // 匹配 canvas 尺寸
          if (captureCanvas.width !== vw || captureCanvas.height !== vh) {
            captureCanvas.width = vw
            captureCanvas.height = vh
          }
          captureCtx.drawImage(cameraVideo, 0, 0, vw, vh)
          const imageData = captureCtx.getImageData(0, 0, vw, vh)

          const symbols: ZBarSymbol[] = await scanImageData(imageData, zbarScanner!)

          if (symbols && symbols.length > 0) {
            const barcode = symbols[0].decode('utf-8')
            if (barcode) {
              stopCamera()
              playBeep()
              onScanned(barcode)
              return
            }
          }
        } catch (e: any) {
          // decode may throw occasionally (e.g. WASM memory); ignore and continue scanning
          console.debug('[useScanner] Frame decode error:', e?.name || e?.message)
        }

        scanLoopTimer = setTimeout(scanFrame, 150)
      }

      scanFrame()
      cameraTimeout = setTimeout(() => stopCamera(), 30000)
      return true
    } catch (e: any) {
      console.error('[useScanner] Camera start failed:', e?.name || e?.message || e)
      await stopCamera()
      return false
    }
  }

  async function stopCamera() {
    cameraActive = false

    if (scanLoopTimer) {
      clearTimeout(scanLoopTimer)
      scanLoopTimer = null
    }

    if (cameraTimeout) {
      clearTimeout(cameraTimeout)
      cameraTimeout = null
    }

    // Stop all tracks (close camera)
    if (cameraStream) {
      for (const track of cameraStream.getTracks()) {
        track.stop()
      }
      cameraStream = null
    }

    if (cameraVideo) {
      cameraVideo.pause()
      cameraVideo.srcObject = null
      cameraVideo.remove()
      cameraVideo = null
    }
  }

  return { startScan, stopScan, startCamera, stopCamera, playBeep, isValidStoreBarcode }
}
