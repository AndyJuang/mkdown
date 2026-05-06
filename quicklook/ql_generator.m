#import <Foundation/Foundation.h>
#import <QuickLook/QuickLook.h>

OSStatus GeneratePreviewForURL(void *thisInterface,
                               QLPreviewRequestRef preview,
                               CFURLRef url,
                               CFStringRef contentTypeUTI,
                               CFDictionaryRef options)
{
    @autoreleasepool {
        NSString *md = [NSString stringWithContentsOfURL:(__bridge NSURL *)url
                                               encoding:NSUTF8StringEncoding
                                                  error:nil];
        if (!md) return noErr;

        // Load marked.js from bundle Resources
        NSBundle *bundle = [NSBundle bundleWithIdentifier:@"com.mkdown.quicklook"];
        NSString *js = @"";
        if (bundle) {
            NSURL *jsURL = [bundle URLForResource:@"marked.min" withExtension:@"js"];
            if (jsURL) {
                js = [NSString stringWithContentsOfURL:jsURL
                                             encoding:NSUTF8StringEncoding
                                                error:nil] ?: @"";
            }
        }

        // Escape for JS template literal
        md = [md stringByReplacingOccurrencesOfString:@"\\"  withString:@"\\\\"];
        md = [md stringByReplacingOccurrencesOfString:@"`"   withString:@"\\`"];
        md = [md stringByReplacingOccurrencesOfString:@"${"  withString:@"\\${"];

        NSString *css =
            @"body{font-family:-apple-system,'PingFang TC','Heiti TC',sans-serif;"
             "max-width:900px;margin:2em auto;padding:0 2em;"
             "line-height:1.75;color:#24292e;background:#fff}"
             "h1,h2,h3,h4,h5,h6{font-weight:600;margin-top:1.2em;margin-bottom:.5em}"
             "h1{font-size:2em;border-bottom:1px solid #eaecef;padding-bottom:.3em}"
             "h2{font-size:1.5em;border-bottom:1px solid #eaecef;padding-bottom:.3em}"
             "h5,h6{color:#6a737d}"
             "code{font-family:Menlo,Monaco,monospace;font-size:87%;"
             "background:rgba(27,31,35,.07);border-radius:3px;padding:.1em .35em}"
             "pre{background:#f6f8fa;padding:1em;border-radius:6px;overflow-x:auto;"
             "margin:.8em 0}"
             "pre code{background:none;padding:0}"
             "blockquote{border-left:4px solid #dfe2e5;color:#525a61;"
             "padding:0 1em;margin:.8em 0}"
             "a{color:#0366d6;text-decoration:none}"
             "table{border-collapse:collapse;width:100%;margin:.8em 0}"
             "th{background:#f0f3f6;font-weight:600}"
             "th,td{border:1px solid #dfe2e5;padding:6px 13px}"
             "tr:nth-child(even){background:#f6f8fa}"
             "img{max-width:100%}"
             "hr{border:none;border-top:1px solid #eaecef;margin:1.5em 0}"
             "@media(prefers-color-scheme:dark){"
             "body{color:#c9d1d9;background:#0d1117}"
             "h1,h2{border-bottom-color:#21262d}"
             "h5,h6{color:#8b949e}"
             "code{background:rgba(110,118,129,.18)}"
             "pre{background:#161b22}"
             "blockquote{color:#969fa8;border-left-color:#3b434b}"
             "a{color:#58a6ff}"
             "th{background:#161b22;color:#e6edf3}"
             "th,td{border-color:#30363d}"
             "tr:nth-child(even){background:#161b22}"
             "tr{background:#0d1117}"
             "hr{border-top-color:#21262d}"
             "}";

        NSString *fallback =
            @"<script>"
             "if(typeof marked==='undefined'){"
             "document.getElementById('c').innerHTML="
             "'<pre style=\"white-space:pre-wrap\">'+"
             "document.getElementById('c').textContent+'</pre>';}"
             "</script>";

        NSString *html = [NSString stringWithFormat:
            @"<!DOCTYPE html><html><head><meta charset='utf-8'>"
             "<style>%@</style></head><body>"
             "<div id='c'></div>"
             "<script>%@</script>"
             "<script>"
             "if(typeof marked!=='undefined'){"
             "document.getElementById('c').innerHTML=marked.parse(`%@`);"
             "}else{"
             "document.getElementById('c').textContent=`%@`;"
             "}"
             "</script>"
             "%@"
             "</body></html>",
            css, js, md, md, fallback];

        NSData *data = [html dataUsingEncoding:NSUTF8StringEncoding];
        QLPreviewRequestSetDataRepresentation(
            preview,
            (__bridge CFDataRef)data,
            CFSTR("public.html"),
            nil
        );
    }
    return noErr;
}

void CancelPreviewGeneration(void *thisInterface, QLPreviewRequestRef preview)
{
    (void)thisInterface; (void)preview;
}
