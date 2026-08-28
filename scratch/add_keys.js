const fs = require('fs');
const pkgPath = 'IDE/vscode/extensions/copilot/package.json';
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

const props = pkg.contributes.configuration[0].properties;

const newProps = {
    "hugos.modelfusion.innovationLevel": { "type": "string", "default": "medium", "description": "Innovation level" },
    "hugos.modelfusion.topK": { "type": "number", "default": 40, "description": "Top K sampling parameter" },
    "hugos.modelfusion.sinqNbits": { "type": "number", "default": 4, "description": "SINQ quantization nbits" },
    "hugos.modelfusion.sinqGroupSize": { "type": "number", "default": 128, "description": "SINQ group size" },
    "hugos.modelfusion.sinqTilingMode": { "type": "string", "default": "auto", "description": "SINQ tiling mode" },
    "hugos.modelfusion.sinqMethod": { "type": "string", "default": "default", "description": "SINQ method" },
    "hugos.modelfusion.weightFormat": { "type": "string", "default": "default", "description": "Weight format" },
    "hugos.modelfusion.port": { "type": "number", "default": 5000, "description": "API Port" },
    "hugos.modelfusion.reportPath": { "type": "string", "default": "", "description": "Report path" },
    "hugos.modelfusion.reportType": { "type": "string", "default": "json", "description": "Report type" },
    "hugos.modelfusion.context": { "type": "string", "default": "", "description": "Context" },
    "hugos.modelfusion.mlConfidenceThreshold": { "type": "number", "default": 0.5, "description": "ML confidence threshold" },
    "hugos.modelfusion.mlEnsembleMethod": { "type": "string", "default": "default", "description": "ML ensemble method" },
    "hugos.modelfusion.mlCleanupDays": { "type": "number", "default": 7, "description": "ML cleanup days" }
};

Object.assign(props, newProps);

fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 4));
console.log('Added missing keys.');
