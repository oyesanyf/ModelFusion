import os

target_str = 'try{Gi.mkdirSync(no.dirname(s),{recursive:!0});let g=no.join(r,"db","hf_models.db");if(Gi.existsSync(g)){let f=Gi.existsSync(s),h=f?Gi.statSync(s).size:0;if(!f||h<1e5){let y=`Copying pre-populated database from ${g} to ${s}...`;this._logService.info(`ModelFusionProvider: ${y}`),this._outputChannel.appendLine(`[DB] ${y}`),Gi.copyFileSync(g,s),this._logService.info("ModelFusionProvider: Database successfully pre-populated!"),this._outputChannel.appendLine("[DB] Database successfully pre-populated!")}}}catch(g){this._logService.error(`ModelFusionProvider: Failed to initialize/pre-populate database: ${g.message}`),this._outputChannel.appendLine(`[DB ERROR] ${g.message}`)}let c=o.get("ovModelDir","")||no.join(gg.homedir(),".hugos-ide","ov_models"),l=o.get("getvino",!1);try{let g=no.join(r,"ov_models");if(Gi.existsSync(g)){let f=Gi.readdirSync(g).filter(h=>Gi.statSync(no.join(g,h)).isDirectory());for(let h of f){let y=no.join(c,h);if(!Gi.existsSync(y)){this._outputChannel.appendLine(`[OV] First launch: copying bundled model ${h} to ${y}...`),Gi.mkdirSync(y,{recursive:!0});let v=no.join(g,h);for(let _ of Gi.readdirSync(v)){let w=no.join(v,_);Gi.statSync(w).isFile()&&Gi.copyFileSync(w,no.join(y,_))}this._outputChannel.appendLine(`[OV] Copied starter model: ${h}`)}}}}catch(g){this._outputChannel.appendLine(`[OV] Warning: Could not copy bundled models: ${g.message}`)}'

replacement_str = 'let c=o.get("ovModelDir","")||no.join(gg.homedir(),".hugos-ide","ov_models"),l=o.get("getvino",!1);setTimeout(async()=>{try{Gi.mkdirSync(no.dirname(s),{recursive:!0});let g=no.join(r,"db","hf_models.db");if(Gi.existsSync(g)){let f=Gi.existsSync(s),h=f?Gi.statSync(s).size:0;if(!f||h<1e5){let y=`Copying pre-populated database from ${g} to ${s}...`;this._logService.info(`ModelFusionProvider: ${y}`),this._outputChannel.appendLine(`[DB] ${y}`),Gi.copyFileSync(g,s),this._logService.info("ModelFusionProvider: Database successfully pre-populated!"),this._outputChannel.appendLine("[DB] Database successfully pre-populated!")}}}catch(g){this._outputChannel.appendLine(`[DB ERROR] ${g.message}`)}try{let g=no.join(r,"ov_models");if(Gi.existsSync(g)){let f=Gi.readdirSync(g).filter(h=>Gi.statSync(no.join(g,h)).isDirectory());for(let h of f){let y=no.join(c,h);if(!Gi.existsSync(y)){this._outputChannel.appendLine(`[OV] First launch: copying bundled model ${h} to ${y}...`),Gi.mkdirSync(y,{recursive:!0});let v=no.join(g,h);for(let _ of Gi.readdirSync(v)){let w=no.join(v,_);Gi.statSync(w).isFile()&&Gi.copyFileSync(w,no.join(y,_))}this._outputChannel.appendLine(`[OV] Copied starter model: ${h}`)}}}}catch(g){this._outputChannel.appendLine(`[OV] Warning: Could not copy bundled models: ${g.message}`)}},10);'

base_dir = r"d:\harfile\ModelFusion\IDE"
count = 0
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file == "extension.js" and "copilot" in root and "dist" in root:
            full_path = os.path.join(root, file)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            if target_str in content:
                content = content.replace(target_str, replacement_str)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Patched non-blocking startup in {full_path}")
                count += 1
            else:
                print(f"Target string not found in {full_path}")

print(f"Total files updated: {count}")
