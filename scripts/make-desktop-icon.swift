import AppKit
let root = CommandLine.arguments[1]
let fm = FileManager.default
try fm.createDirectory(atPath: root + "/icon.iconset", withIntermediateDirectories: true)
for size in [16,32,128,256,512] {
  for scale in [1,2] {
    let px=size*scale
    let bitmap=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:px,pixelsHigh:px,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current=NSGraphicsContext(bitmapImageRep:bitmap)
    let s=CGFloat(px)
    NSColor(calibratedWhite:0.12,alpha:1).setFill()
    NSBezierPath(roundedRect:NSRect(x:s*0.06,y:s*0.06,width:s*0.88,height:s*0.88),xRadius:s*0.19,yRadius:s*0.19).fill()
    NSColor(calibratedWhite:0.97,alpha:1).setStroke()
    let p=NSBezierPath(roundedRect:NSRect(x:s*0.26,y:s*0.34,width:s*0.48,height:s*0.39),xRadius:s*0.075,yRadius:s*0.075)
    p.lineWidth=s*0.038;p.stroke()
    let tail=NSBezierPath();tail.move(to:NSPoint(x:s*0.30,y:s*0.37));tail.line(to:NSPoint(x:s*0.30,y:s*0.23));tail.line(to:NSPoint(x:s*0.44,y:s*0.34));tail.lineWidth=s*0.038;tail.lineJoinStyle = .round;tail.stroke()
    NSColor(calibratedWhite:0.97,alpha:1).setFill()
    for x in [0.39,0.5,0.61] {NSBezierPath(ovalIn:NSRect(x:s*(x-0.02),y:s*0.515,width:s*0.04,height:s*0.04)).fill()}
    NSGraphicsContext.restoreGraphicsState()
    let suffix=scale==2 ? "@2x" : ""
    try bitmap.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:"\(root)/icon.iconset/icon_\(size)x\(size)\(suffix).png"))
  }
}
