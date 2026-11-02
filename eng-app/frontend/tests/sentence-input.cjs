const assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
const m={};new Function('exports',ts.transpileModule(fs.readFileSync(require.resolve('../src/sentenceInput.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText)(m);
const shapes=[[1,4,2,3],[1,4,2,4,1,4],[1,4,2,3,1,4]];
for(const [value,expected] of [['',false],['I want to',false],['I want to have',false],['I want to have a',false],['I want to have a meal',true],['I want to eat',true],['i  want to eat.',true],['I want to eot',true],['I want to ea',false],['I want to eat a meal',true]])assert.equal(m.sentenceReady(value,shapes),expected,value);
console.log('10 sentence readiness cases passed');
