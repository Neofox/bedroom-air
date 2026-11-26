import Foundation
import AppKit
import CoreImage

guard CommandLine.arguments.count == 2 else {
    FileHandle.standardError.write(Data("Usage: provide a setup PIN on stdin and an output PNG path as the argument.\n".utf8))
    exit(1)
}
let raw = String(decoding: FileHandle.standardInput.readDataToEndOfFile(), as: UTF8.self)
    .trimmingCharacters(in: .whitespacesAndNewlines)
guard raw.count == 8, raw.allSatisfy(\.isNumber), let pin = UInt64(raw) else { exit(1) }
let payload = String((UInt64(10) << 31) | (UInt64(1) << 28) | pin, radix: 36, uppercase: true)
let uri = "X-HM://" + String(repeating: "0", count: 9 - payload.count) + payload + "BAIR"
let f = CIFilter(name:"CIQRCodeGenerator", parameters:["inputMessage":Data(uri.utf8),"inputCorrectionLevel":"M"])!
let qr = f.outputImage!
let context = CIContext()
let cg = context.createCGImage(qr, from:qr.extent)!
let side = 400
let bitmap = NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:side,pixelsHigh:450,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
let graphics = NSGraphicsContext(bitmapImageRep:bitmap)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = graphics
let canvas = graphics.cgContext
canvas.setFillColor(NSColor.white.cgColor)
canvas.fill(CGRect(x:0,y:0,width:side,height:450))
canvas.interpolationQuality = .none
let tile = Int(qr.extent.width)
let dimension = tile * (320 / tile)
canvas.draw(cg,in:CGRect(x:(side-dimension)/2,y:76,width:dimension,height:dimension))
func center(_ s:String, _ y:Int,_ font:NSFont) {
    let attrs:[NSAttributedString.Key:Any] = [.font:font,.foregroundColor:NSColor.black]
    let size=(s as NSString).size(withAttributes:attrs)
    (s as NSString).draw(at:NSPoint(x:(CGFloat(side)-size.width)/2,y:CGFloat(y)),withAttributes:attrs)
}
center("Bedroom Air",399,NSFont.systemFont(ofSize:24,weight:.semibold))
center("\(raw.prefix(3))-\(raw.dropFirst(3).prefix(2))-\(raw.suffix(3))",28,NSFont.monospacedDigitSystemFont(ofSize:26,weight:.medium))
NSGraphicsContext.restoreGraphicsState()
let image = CIImage(bitmapImageRep:bitmap)!
let detector = CIDetector(ofType:CIDetectorTypeQRCode,context:context,options:[CIDetectorAccuracy:CIDetectorAccuracyHigh])!
guard detector.features(in:image).contains(where:{($0 as? CIQRCodeFeature)?.messageString == uri}) else { exit(2) }
let out = URL(fileURLWithPath:CommandLine.arguments[1])
try bitmap.representation(using:.png,properties:[:])!.write(to:out,options:.atomic)
try FileManager.default.setAttributes([.posixPermissions:0o600],ofItemAtPath:out.path)
print("Home pairing QR encoded and decoded successfully")
