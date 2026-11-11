const {defineConfig}=require('/workspace/mtgo-data/node_modules/@playwright/test');
module.exports=defineConfig({
 testDir:'/workspace/mtgo-data/tests/browser',
 testMatch:['frontend-resource-loading.spec.js','frontend-sharing-keyboard.spec.js'],
 workers:1,retries:0,reporter:'line',outputDir:'/workspace/scratch/pages-slimming/browser-results',
 use:{baseURL:'http://127.0.0.1:4173',browserName:'chromium',launchOptions:{executablePath:'/usr/bin/chromium'},trace:'retain-on-failure'},
 webServer:{command:'node /workspace/mtgo-data/tests/browser/static-server.js',cwd:'/workspace/scratch/pages-slimming/extracted',url:'http://127.0.0.1:4173/stats/catalog.json',reuseExistingServer:false}
});
