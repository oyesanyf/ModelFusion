const fs = require('fs');
const path = require('path');

function generateWix(srcDir, outputFile) {
    let dirIdCounter = 1;
    let fileIdCounter = 1;
    let componentIdCounter = 1;

    function escapeXml(unsafe) {
        return unsafe.replace(/[<>&'"]/g, (c) => {
            switch (c) {
                case '<': return '&lt;';
                case '>': return '&gt;';
                case '&': return '&amp;';
                case '\'': return '&apos;';
                case '"': return '&quot;';
            }
        });
    }

    const directories = [];
    const components = [];

    function walk(currentPath, parentDirId) {
        const items = fs.readdirSync(currentPath);
        for (const item of items) {
            // Skip .msi, .wxs, .wixpdb, .log, and large DB from installer payload to keep installer light
            if (item.endsWith('.msi') || item.endsWith('.wxs') || item.endsWith('.wixpdb') || item.endsWith('.log') || item.endsWith('.db') || item === '.git') {
                continue;
            }
            const itemPath = path.join(currentPath, item);
            const stat = fs.statSync(itemPath);

            if (stat.isDirectory()) {
                const dirId = `dir_${dirIdCounter++}`;
                directories.push({
                    id: dirId,
                    name: item,
                    parentId: parentDirId
                });
                walk(itemPath, dirId);
            } else {
                const relSource = path.relative(path.dirname(outputFile), itemPath);
                components.push({
                    id: `cmp_${componentIdCounter++}`,
                    fileId: `fil_${fileIdCounter++}`,
                    source: relSource,
                    directoryId: parentDirId
                });
            }
        }
    }

    walk(srcDir, 'INSTALLFOLDER');

    const dirMap = { 'INSTALLFOLDER': { id: 'INSTALLFOLDER', children: [] } };
    for (const dir of directories) {
        dirMap[dir.id] = { id: dir.id, name: dir.name, children: [] };
    }
    for (const dir of directories) {
        dirMap[dir.parentId].children.push(dirMap[dir.id]);
    }

    function renderDirTree(node, indent) {
        let xml = '';
        for (const child of node.children) {
            xml += `${indent}<Directory Id="${child.id}" Name="${escapeXml(child.name)}">\n`;
            xml += renderDirTree(child, indent + '  ');
            xml += `${indent}</Directory>\n`;
        }
        return xml;
    }

    const directoryTreeXml = renderDirTree(dirMap['INSTALLFOLDER'], '        ');

    let componentsXml = '    <ComponentGroup Id="BrowserFilesComponents">\n';
    for (const cmp of components) {
        const dirAttr = ` Directory="${cmp.directoryId}"`;
        componentsXml += `      <Component Id="${cmp.id}" Guid="*"${dirAttr}>\n`;
        componentsXml += `        <File Id="${cmp.fileId}" Source="${escapeXml(cmp.source)}" KeyPath="yes" />\n`;
        componentsXml += `      </Component>\n`;
    }
    componentsXml += '    </ComponentGroup>';

    const buildNumPath = path.join(__dirname, 'build_number.txt');
    let buildNumber = 0;
    try {
        buildNumber = parseInt(fs.readFileSync(buildNumPath, 'utf-8').trim(), 10);
    } catch (e) {}
    if (isNaN(buildNumber) || !buildNumber) { buildNumber = 1; }
    buildNumber++;
    fs.writeFileSync(buildNumPath, buildNumber.toString(), 'utf-8');

    const version = `1.0.${buildNumber}`;
    const iconPath = path.join(path.dirname(__dirname), 'IDE', 'hugos.ico');

    const wxsContent = `<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  <Package Name="HugOS Browser" Manufacturer="HugOS Team" Version="${version}" UpgradeCode="e98c7d08-91cb-4248-bfa5-765c96ddeca6" Scope="perUser">
    <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." Schedule="afterInstallInitialize" AllowSameVersionUpgrades="yes" />

    <MediaTemplate EmbedCab="yes" />

    <Icon Id="HugOSBrowserIcon.ico" SourceFile="${escapeXml(iconPath)}" />
    <Property Id="ARPPRODUCTICON" Value="HugOSBrowserIcon.ico" />
    <Property Id="ARPHELPLINK" Value="https://github.com/oyesanyf/ModelFusion" />
    <Property Id="ARPURLINFOABOUT" Value="https://github.com/oyesanyf/ModelFusion" />

    <StandardDirectory Id="LocalAppDataFolder">
      <Directory Id="INSTALLFOLDER" Name="HugOS Browser">
${directoryTreeXml}
      </Directory>
    </StandardDirectory>

    <StandardDirectory Id="ProgramMenuFolder">
      <Directory Id="ApplicationProgramsFolder" Name="HugOS Browser" />
    </StandardDirectory>
    <StandardDirectory Id="DesktopFolder">
      <Component Id="ApplicationShortcutDesktop" Guid="*">
        <Shortcut Id="ApplicationDesktopShortcut" Name="HugOS Browser" Target="[INSTALLFOLDER]Chromium-win32-x64\\hugos-browser.bat" WorkingDirectory="INSTALLFOLDER" Icon="HugOSBrowserIcon.ico" />
        <RegistryValue Root="HKCU" Key="Software\\HugOSTeam\\HugOSBrowser" Name="desktop_shortcut" Type="integer" Value="1" KeyPath="yes" />
      </Component>
    </StandardDirectory>

    <DirectoryRef Id="ApplicationProgramsFolder">
      <Component Id="ApplicationShortcut" Guid="*">
        <Shortcut Id="ApplicationStartMenuShortcut" Name="HugOS Browser" Target="[INSTALLFOLDER]Chromium-win32-x64\\hugos-browser.bat" Directory="ApplicationProgramsFolder" WorkingDirectory="INSTALLFOLDER" Icon="HugOSBrowserIcon.ico" />
        <RemoveFolder Id="CleanUpShortcuts" On="uninstall" />
        <RegistryValue Root="HKCU" Key="Software\\HugOSTeam\\HugOSBrowser" Name="installed" Type="integer" Value="1" KeyPath="yes" />
      </Component>
    </DirectoryRef>

    <Feature Id="Main">
      <ComponentGroupRef Id="BrowserFilesComponents" />
      <ComponentRef Id="ApplicationShortcut" />
      <ComponentRef Id="ApplicationShortcutDesktop" />
    </Feature>

${componentsXml}
  </Package>
</Wix>
`;

    try { if (fs.existsSync(outputFile)) fs.unlinkSync(outputFile); } catch(e) {}
    fs.writeFileSync(outputFile, wxsContent, 'utf8');
    console.log(`Successfully generated WiX source at ${outputFile}`);
}

const args = process.argv.slice(2);
if (args.length < 2) {
    console.error('Usage: node generate_wix.js <src_dir> <output_file>');
    process.exit(1);
}

generateWix(args[0], args[1]);
