const http=require("http"),fs=require("fs"),path=require("path");
const root=path.join(__dirname,"..","app");
const types={".html":"text/html;charset=utf-8",".js":"text/javascript",".css":"text/css",".json":"application/json",".webmanifest":"application/manifest+json",".png":"image/png",".svg":"image/svg+xml"};
http.createServer((q,r)=>{let p=decodeURIComponent(q.url.split("?")[0]);if(p.endsWith("/"))p+="index.html";
const f=path.join(root,p);if(!f.startsWith(root)||!fs.existsSync(f)){r.writeHead(404);return r.end("404")}
r.writeHead(200,{"Content-Type":types[path.extname(f)]||"application/octet-stream"});fs.createReadStream(f).pipe(r)}).listen(process.env.PORT||5173);
