import Cocoa
import QuickLookUI
import UniformTypeIdentifiers

// Principal class referenced in Info.plist NSExtensionPrincipalClass
@objc(PreviewViewController)
final class PreviewViewController: NSViewController, QLPreviewingController {

    override var nibName: NSNib.Name? { nil }

    override func loadView() {
        view = NSView(frame: NSRect(x: 0, y: 0, width: 900, height: 1200))
    }

    // ── macOS 10.15 required stub ─────────────────────────────────────────────
    func preparePreviewOfFile(at url: URL, completionHandler handler: @escaping (Error?) -> Void) {
        handler(nil)
    }

    // ── macOS 12+ data-based preview (returns HTML, QL renders it) ────────────
    @available(macOS 12.0, *)
    func providePreview(for request: QLFilePreviewRequest,
                        completionHandler handler: @escaping (QLPreviewReply?, Error?) -> Void) {

        let url = request.fileURL

        guard let rawMD = try? String(contentsOf: url, encoding: .utf8) else {
            handler(nil, nil)
            return
        }

        // Load marked.js from Resources (downloaded/cached by install_quicklook.py)
        let bundle  = Bundle(for: PreviewViewController.self)
        let markedJS: String
        if let jsURL = bundle.url(forResource: "marked.min", withExtension: "js"),
           let js    = try? String(contentsOf: jsURL, encoding: .utf8) {
            markedJS = js
        } else {
            markedJS = ""
        }

        // Escape for JS template literal
        let md = rawMD
            .replacingOccurrences(of: "\\",  with: "\\\\")
            .replacingOccurrences(of: "`",   with: "\\`")
            .replacingOccurrences(of: "${",  with: "\\${")

        let css = """
        body{font-family:-apple-system,'PingFang TC','Heiti TC',sans-serif;
             max-width:900px;margin:2em auto;padding:0 2em;
             line-height:1.75;color:#24292e;background:#fff}
        h1,h2,h3,h4,h5,h6{font-weight:600;margin-top:1.2em;margin-bottom:.5em}
        h1{font-size:2em;border-bottom:1px solid #eaecef;padding-bottom:.3em}
        h2{font-size:1.5em;border-bottom:1px solid #eaecef;padding-bottom:.3em}
        h5,h6{color:#6a737d}
        code{font-family:Menlo,Monaco,monospace;font-size:87%;
             background:rgba(27,31,35,.07);border-radius:3px;padding:.1em .35em}
        pre{background:#f6f8fa;padding:1em;border-radius:6px;overflow-x:auto;margin:.8em 0}
        pre code{background:none;padding:0}
        blockquote{border-left:4px solid #dfe2e5;color:#525a61;padding:0 1em;margin:.8em 0}
        a{color:#0366d6;text-decoration:none}
        table{border-collapse:collapse;width:100%;margin:.8em 0}
        th{background:#f0f3f6;font-weight:600}
        th,td{border:1px solid #dfe2e5;padding:6px 13px}
        tr:nth-child(even){background:#f6f8fa}
        img{max-width:100%}
        hr{border:none;border-top:1px solid #eaecef;margin:1.5em 0}
        @media(prefers-color-scheme:dark){
          body{color:#c9d1d9;background:#0d1117}
          h1,h2{border-bottom-color:#21262d}
          h5,h6{color:#8b949e}
          code{background:rgba(110,118,129,.18)}
          pre{background:#161b22}
          blockquote{color:#969fa8;border-left-color:#3b434b}
          a{color:#58a6ff}
          th{background:#161b22;color:#e6edf3}
          th,td{border-color:#30363d}
          tr:nth-child(even){background:#161b22}
          tr{background:#0d1117}
          hr{border-top-color:#21262d}
        }
        """

        let html = """
        <!DOCTYPE html>
        <html>
        <head><meta charset='utf-8'><style>\(css)</style></head>
        <body>
        <div id='c'></div>
        <script>\(markedJS)</script>
        <script>
        if(typeof marked!=='undefined'){
            document.getElementById('c').innerHTML=marked.parse(`\(md)`);
        }else{
            var pre=document.createElement('pre');
            pre.style.whiteSpace='pre-wrap';
            pre.textContent=`\(md)`;
            document.getElementById('c').appendChild(pre);
        }
        </script>
        </body>
        </html>
        """

        let reply = QLPreviewReply(
            dataOfContentType: .html,
            contentSize: CGSize(width: 900, height: 1200)
        ) { _ in
            return html.data(using: .utf8)!
        }

        handler(reply, nil)
    }
}
