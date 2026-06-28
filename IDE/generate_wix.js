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
                components.push({
                    id: `cmp_${componentIdCounter++}`,
                    fileId: `fil_${fileIdCounter++}`,
                    source: itemPath,
                    directoryId: parentDirId
                });
            }
        }
    }

    // Start walking the source directory. Root is 'INSTALLFOLDER'
    walk(srcDir, 'INSTALLFOLDER');

    // Build the directory tree
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

    // Render components
    let componentsXml = '    <ComponentGroup Id="AppFilesComponents" Directory="INSTALLFOLDER">\n';
    for (const cmp of components) {
        const dirAttr = cmp.directoryId === 'INSTALLFOLDER' ? '' : ` Directory="${cmp.directoryId}"`;
        componentsXml += `      <Component Id="${cmp.id}" Guid="*"${dirAttr}>\n`;
        componentsXml += `        <File Id="${cmp.fileId}" Source="${escapeXml(cmp.source)}" KeyPath="yes" />\n`;
        componentsXml += `      </Component>\n`;
    }
    componentsXml += '    </ComponentGroup>';

    const wxsContent = `<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  <Package Name="HugOS IDE" Manufacturer="HugOS Team" Version="1.126.0" UpgradeCode="d77b7e06-80ba-4137-bcf4-654b95ccebc5">
    <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />

    <MediaTemplate EmbedCab="yes" />

    <Icon Id="HugOSIcon.ico" SourceFile="D:\\harfile\\ModelFusion\\IDE\\hugos.ico" />

    <StandardDirectory Id="ProgramFiles64Folder">
      <Directory Id="INSTALLFOLDER" Name="HugOS IDE">
${directoryTreeXml}
      </Directory>
    </StandardDirectory>

    <StandardDirectory Id="ProgramMenuFolder">
      <Directory Id="ApplicationProgramsFolder" Name="HugOS IDE" />
    </StandardDirectory>
    <StandardDirectory Id="DesktopFolder" />

    <DirectoryRef Id="ApplicationProgramsFolder">
      <Component Id="ApplicationShortcut" Guid="*">
        <Shortcut Id="ApplicationStartMenuShortcut" Name="HugOS IDE" Target="[INSTALLFOLDER]HugOS.exe" Directory="ApplicationProgramsFolder" WorkingDirectory="INSTALLFOLDER" Icon="HugOSIcon.ico" />
        <RemoveFolder Id="CleanUpShortcuts" On="uninstall" />
        <RegistryValue Root="HKCU" Key="Software\\HugOSTeam\\HugOSIDE" Name="installed" Type="integer" Value="1" KeyPath="yes" />
      </Component>
    </DirectoryRef>

    <DirectoryRef Id="DesktopFolder">
      <Component Id="ApplicationShortcutDesktop" Guid="*">
        <Shortcut Id="ApplicationDesktopShortcut" Name="HugOS IDE" Target="[INSTALLFOLDER]HugOS.exe" Directory="DesktopFolder" WorkingDirectory="INSTALLFOLDER" Icon="HugOSIcon.ico" />
        <RegistryValue Root="HKCU" Key="Software\\HugOSTeam\\HugOSIDE" Name="desktop_shortcut" Type="integer" Value="1" KeyPath="yes" />
      </Component>
    </DirectoryRef>

    <Feature Id="Main">
      <ComponentGroupRef Id="AppFilesComponents" />
      <ComponentRef Id="ApplicationShortcut" />
      <ComponentRef Id="ApplicationShortcutDesktop" />
    </Feature>

${componentsXml}
  </Package>
</Wix>
`;

    fs.writeFileSync(outputFile, wxsContent, 'utf8');
    console.log(`Successfully generated WiX source at ${outputFile}`);
}

const args = process.argv.slice(2);
if (args.length < 2) {
    console.error('Usage: node generate_wix.js <src_dir> <output_file>');
    process.exit(1);
}

generateWix(args[0], args[1]);
