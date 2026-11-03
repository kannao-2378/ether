const assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
const m={};new Function('exports',ts.transpileModule(fs.readFileSync(require.resolve('../src/sentenceInput.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText)(m);
const shapes=[[1,4,2,3],[1,4,2,4,1,4],[1,4,2,3,1,4]];
for(const [value,expected] of [['',false],['I want to',false],['I want to have',false],['I want to have a',false],['I want to have a meal',true],['I want to eat',true],['i  want to eat.',true],['I want to eot',true],['I want to ea',false],['I want to eat a meal',true]])assert.equal(m.sentenceReady(value,shapes),expected,value);
console.log('10 sentence readiness cases passed');

for(const [raw,lengths,expected] of [
 ['wantto',[4,2],'want to'],['listentomusic',[6,2,5],'listen to music'],
 ['iwanttodrinkwater',[1,4,2,5,5],'i want to drink water'],
 ['i want to drink water',[1,4,2,5,5],'i want to drink water'],
 ['iwantt',[1,4,2,5,5],'i want t'],['iwanttdrink',[1,4,2,5,5],'i want td rink'],
 ['drink',[5],'drink'],["idon’tknow",[1,5,4],"i don’t know"],
 ['iwanttodrinkwater.',[1,4,2,5,5],'i want to drink water.'],
 ['', [1,4,2],'']])assert.equal(m.spaceByLengths(raw,lengths).value,expected,raw);
assert.deepEqual(m.spaceByLengths('i wantto',[1,4,2],3),{value:'i want to',cursor:3});
// Backspace at a generated separator deletes the preceding letter, not a stuck space.
assert.equal(m.spaceByLengths('i wan to',[1,4,2],5).cursor,5);
console.log('12 automatic spacing/edit cases passed');
