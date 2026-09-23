import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',timeout:60000,workers:1,use:{baseURL:process.env.PLAYWRIGHT_BASE_URL||'http://localhost:3000',headless:true,channel:'chrome',viewport:{width:1440,height:1050}},reporter:'list'});
