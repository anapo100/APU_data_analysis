/* Offline click-by-click presentation. Each group is revealed atomically. */
(()=>{'use strict';
const $=s=>document.querySelector(s),slides=[...document.querySelectorAll('.slide')];
const plan=[{"entry":{"selectors":[".cover-rule",".cover-desc",".cover-bottom"],"content":"압력·전류·운전 상태로 고장 전 점검 후보를 찾는 프로젝트 소개 / Z-score·Isolation Forest·Local Outlier Factor 비교"},"steps":[]},{"entry":{"selectors":[".agenda > div:nth-child(1)",".agenda > div:nth-child(2)",".agenda > div:nth-child(3)",".agenda > div:nth-child(4)",".agenda > div:nth-child(5)",".agenda > div:nth-child(6)"],"content":"문제와 데이터 / 주기 전처리와 특징 / 시계열 분석 / 모델 비교와 평가 / 오탐·미탐 해석 / 결론과 다음 단계"},"steps":[]},{"entry":{"selectors":[".team-presenter"],"content":"이하일: 팀장·프로젝트 총괄·발표"},"steps":[{"step":1,"selectors":[".team-others"],"content":"차승윤·신승원·김제환·전미소와 각 담당 역할"}]},{"entry":{"selectors":[".references"],"content":"UCI 데이터셋 → 운전 주기 단위 분석 / 선행 분석 사례 → 동일 특징·조건에서 모델 비교 / Predictive maintenance based on anomaly detection using deep learning for air production unit in the railway industry → 고장 기록으로 평가 기준 구성"},"steps":[]},{"entry":{"selectors":[".lead",".warning-line",".target"],"content":"고장 24시간 전부터 2시간 전까지의 전조 평가 구간 / 검증 9건 중 최소 7건 탐지 목표"},"steps":[{"step":1,"selectors":[".rule-row"],"content":"주기 평가와 경보 평가 구분 / 발송 후 1시간 추가 경보 제한"}]},{"entry":{"selectors":[".big-number",".data-layout > div:first-child > p",".sensor-list",".data-facts"],"content":"센서 기록 1,516,948개 카운트 후 나머지 정보 자동 표시 / 약 10초 간격 / TP3 압력, Motor_current 전류, COMP 0 가동·1 대기, 시각 / 3~7월 분석 / 전문가 고장 기록 21구간을 16사건으로 정리"},"steps":[]},{"entry":{"selectors":[".lead",".cycle-strip",".cycle-caption"],"content":"가동 시작→대기→다음 가동 시작 / 가동 2·대기 5구간"},"steps":[{"step":1,"selectors":[".process"],"content":"30초 초과 공백 분리→불완전 주기 제외→주기 종료 후 판정"},{"step":2,"selectors":[".bottom-stat"],"content":"전체 완전 주기 10,269개 중 3~7월 분석 7,245개"}]},{"entry":{"selectors":[".wide-chart"],"content":"3~7월 압력·전류·주기 길이 원본 시계열 전체 / 선 일별 중앙값·띠 25~75%·E15/E16 음영"},"steps":[{"step":1,"selectors":[".chart-stats"],"content":"7월 정상→전조: 길이 19.33→8.60분, 전류 2.067→4.424A / 정상 1,663·전조 182주기"}]},{"entry":{"selectors":[".cycle-strip"],"content":"가동 2·대기 5구간"},"steps":[{"step":1,"selectors":[".feature-formula"],"content":"7구간×압력·전류 평균에 전체 주기 길이를 곱함"},{"step":2,"selectors":[".feature-total"],"content":"압력·전류 14개 + 가동·대기 시간 2개 = A16"}]},{"entry":{"selectors":[".model-columns"],"content":"Z-score 평균 이탈 / IF 분리 경로 / LOF 학습 이웃과 차이"},"steps":[{"step":1,"selectors":[".split"],"content":"3~4월 학습→5~6월 검증 설정 선택→7월 평가"}]},{"entry":{"selectors":[".threshold-table",".table-caption"],"content":"검증 탐지 목표별 정상 구간 오탐 표 전체 / 7건 목표 IF 36건 최소"},"steps":[{"step":1,"selectors":[".takeaway"],"content":"8·9건 목표에서는 최소 오탐 모델이 LOF로 변경"}]},{"entry":{"selectors":[".matrix-block:nth-child(1)",".matrix-block:nth-child(2)",".matrix-block:nth-child(3)"],"content":"Z-score 혼동행렬 / P 38.50%, R 79.12%, F1 0.5180 / IF 혼동행렬 / P 69.41%, R 64.84%, F1 0.6705 / LOF 혼동행렬 / P·R 0%, F1 0 / 경보 제한 전 동일 1,845주기"},"steps":[]},{"entry":{"selectors":[".event-top",".event-table"],"content":"Z-score·IF가 전체 3사건 중 E15·E16 공통 탐지 / E14 전조 관측 없음 / LOF 미탐 / 전체 경보·정상 구간 오탐: Z 174·134, IF 61·35, LOF 35·29건"},"steps":[{"step":1,"selectors":[".takeaway"],"content":"첫 경보는 Z가 E15 2.14시간·E16 6.95시간 빠름"}]},{"entry":{"selectors":[".error-chart",".error-heading",".error-caption"],"content":"7월 2일 LOF 오탐과 20.7분 전 정상 비교 차트 전체 / 오탐 5.8029·정상 1.0038·임곗값 2.0152 / 평균 도달거리 0.7127·0.1144"},"steps":[{"step":1,"selectors":[".caution"],"content":"마지막 대기 구간의 전류 특징(B7)에서 정상 주기와 큰 차이 / B7은 대기 5구간 중 마지막 구간의 전류 특징"}]},{"entry":{"selectors":[".error-chart",".error-heading",".error-caption"],"content":"동일 E16 미탐·정탐 원본 비교 차트 전체 / 13.52시간 차이 / 점수 0.5203·0.5573, 임곗값 0.5352 / 주기 길이 12.73·10.57분"},"steps":[{"step":1,"selectors":[".caution"],"content":"놓친 주기는 다른 주기들과 구분하기 어려워 이상 점수가 낮았음"}]},{"entry":{"selectors":[".feature-table"],"content":"7월 IF의 A16·B16·T2 비교 표 전체 / 오탐 35·41·19건, 중앙 선행시간 14.55·18.02·12.51시간"},"steps":[{"step":1,"selectors":[".takeaway"],"content":"T2는 오탐 최소, B16은 중앙 선행시간 최대 / 세 구성 모두 관측 가능 2/2사건 탐지"}]},{"entry":{"selectors":[".conclusion-line",".conclusion-copy"],"content":"IF 선정 조건 / 검증 오탐 36건·7월 전체 경보 61건 / 두 사건 공통 탐지 / Z 174→IF 61 경보 / 첫 경보는 Z가 빠름"},"steps":[{"step":1,"selectors":[".bundle"],"content":"IF 조기경보 20건 중 반복 18건 / 반복을 묶어 점검 단위로 관리"}]},{"entry":{"selectors":[".scope-grid > div:first-child"],"content":"해석 범위: 7월 반복 확인, 관측 가능 2사건, A16·검증 7/9 조건의 선정"},"steps":[{"step":1,"selectors":[".scope-grid > div:last-child > h2",".scope-grid > div:last-child > article:nth-child(2)",".scope-grid > div:last-child > article:nth-child(3)",".scope-grid > div:last-child > article:nth-child(4)"],"content":"개선: 오탐·선행시간 함께 평가 / 1시간 경보 간격·묶음 기준 비교 / 새 기간 자료 확보 후 동일 설정으로 재검증"}]}];
const steps=plan.map(page=>page.steps);
let current=0,step=0;
const fragments=slides.map((slide,n)=>[plan[n].entry,...steps[n]].map((group,groupIndex)=>{
 const found=[...new Set(group.selectors.flatMap(selector=>[...slide.querySelectorAll(selector)]))];
 found.forEach((el,index)=>{el.classList.add('fragment');el.dataset.revealStep=String(groupIndex);el.style.setProperty('--fragment-delay',Math.min(index*35,105)+'ms');
 const kind=el.matches('.chart,.threshold-table,.feature-table,.event-table,.matrices,.matrix-block,.sensor-list,.model-columns')?'evidence':el.matches('.cover-rule')?'rule':el.matches('.cycle-strip,.split,.process')?'flow':el.matches('.takeaway,.caution,.bundle,.feature-total')?'interpret':el.matches('.big-number,.target,.conclusion-line')?'title':'settle';
 el.style.setProperty('--fragment-effect','apu-editorial-'+kind);});return found;
}));
// Slide 7 only: illustrative process line and visual-only count-up.
const cycleSlide=slides[6];
const motionPreference=typeof matchMedia==='function'?matchMedia('(prefers-reduced-motion: reduce)'):null;
let countFrame=null,countToken=0;
const cycleCounts=[...cycleSlide.querySelectorAll('.bottom-stat strong')].map(el=>{
 const finalText=el.textContent.trim(),target=Number(finalText.replace(/,/g,''));
 const actual=document.createElement('span');actual.className='cycle-count-value';actual.textContent=finalText;
 const visual=document.createElement('span');visual.className='cycle-count-visual';visual.setAttribute('aria-hidden','true');visual.textContent=finalText;
 el.textContent='';el.classList.add('cycle-count');el.appendChild(actual);el.appendChild(visual);
 return {actual,visual,finalText,target};
});
function finishCycleMotion(){countToken++;if(countFrame!==null){cancelAnimationFrame(countFrame);countFrame=null;}cycleCounts.forEach(item=>item.visual.textContent=item.finalText);cycleSlide.classList.remove('cycle-flow-active');}
function countCycles(){
 if(motionPreference?.matches||typeof requestAnimationFrame!=='function')return;
 const token=++countToken,start=performance.now();cycleCounts.forEach(item=>item.visual.textContent='0');
 const frame=now=>{if(token!==countToken)return;countFrame=null;const t=Math.min(1,Math.max(0,(now-start)/1000)),eased=1-Math.pow(1-t,3);
  cycleCounts.forEach(item=>item.visual.textContent=t===1?item.finalText:Math.round(item.target*eased).toLocaleString('en-US'));
  if(t<1)countFrame=requestAnimationFrame(frame);
 };
 countFrame=requestAnimationFrame(frame);
}
function syncCycleMotion(previousSlide,previousStep,animate){
 finishCycleMotion();if(current!==6||motionPreference?.matches)return;
 if(previousSlide!==6&&step===0)cycleSlide.classList.add('cycle-flow-active');
 if(animate&&previousSlide===6&&previousStep<2&&step===2)countCycles();
}
if(motionPreference?.addEventListener)motionPreference.addEventListener('change',finishCycleMotion);
// Slide 6: accessible final count, visual count then automatic detail entrance.
const dataSlide=slides[5],dataNumber=dataSlide.querySelector('.data-number-value'),dataDetails=[...dataSlide.querySelectorAll('.data-detail')];
const dataFinal=dataNumber.textContent.trim(),dataTarget=Number(dataFinal.replace(/,/g,''));
const dataActual=document.createElement('span'),dataVisual=document.createElement('span');
dataActual.className='data-count-real';dataActual.textContent=dataFinal;dataVisual.className='data-count-visual';dataVisual.setAttribute('aria-hidden','true');dataVisual.textContent=dataFinal;dataNumber.textContent='';dataNumber.appendChild(dataActual);dataNumber.appendChild(dataVisual);
let dataFrame=null,dataToken=0;
function finishDataMotion(){dataToken++;if(dataFrame!==null){cancelAnimationFrame(dataFrame);dataFrame=null;}dataVisual.textContent=dataFinal;dataSlide.classList.remove('data-count-pending');dataSlide.classList.remove('data-details-enter');dataDetails.forEach(el=>{el.inert=current!==5;el.setAttribute('aria-hidden',String(current!==5));});}
function syncDataMotion(previousSlide){
 finishDataMotion();if(current!==5||previousSlide===5||motionPreference?.matches||typeof requestAnimationFrame!=='function')return;
 const token=++dataToken,start=performance.now();dataSlide.classList.add('data-count-pending');dataVisual.textContent='0';dataDetails.forEach(el=>{el.inert=true;el.setAttribute('aria-hidden','true');});
 const frame=now=>{if(token!==dataToken)return;dataFrame=null;const t=Math.min(1,Math.max(0,(now-start)/1200));dataVisual.textContent=t===1?dataFinal:Math.round(dataTarget*(1-Math.pow(1-t,3))).toLocaleString('en-US');if(t<1){dataFrame=requestAnimationFrame(frame);}else{dataSlide.classList.remove('data-count-pending');dataSlide.classList.add('data-details-enter');dataDetails.forEach(el=>{el.inert=false;el.setAttribute('aria-hidden','false');});}};dataFrame=requestAnimationFrame(frame);
}
if(motionPreference?.addEventListener)motionPreference.addEventListener('change',finishDataMotion);
function fit(){const fullScreen=!!document.fullscreenElement,margin=fullScreen?0:(innerWidth<650?12:40),reservedHeight=fullScreen?0:90;document.documentElement.style.setProperty('--scale',Math.max(.05,Math.min((innerWidth-margin)/1600,(innerHeight-reservedHeight)/900)));}
function render(previousSlide,previousStep,animate){
 slides.forEach((slide,n)=>{const active=n===current;slide.classList.toggle('active',active);slide.classList.toggle('is-entering',active&&n!==previousSlide);slide.setAttribute('aria-hidden',String(!active));slide.inert=!active;
 fragments[n].forEach((group,g)=>group.forEach(el=>{const visible=active&&g<=step;const newlyShown=visible&&animate&&n===previousSlide&&g>previousStep;el.classList.toggle('is-revealing',newlyShown);el.classList.toggle('revealed',visible);el.setAttribute('aria-hidden',String(!visible));el.inert=!visible;}));});
 $('#counter').textContent=`${current+1} / ${slides.length}`;$('#prev').disabled=current===0&&step===0;$('#next').disabled=current===slides.length-1&&step===steps[current].length;
 document.title=`${current+1}. ${slides[current].dataset.title.replace(/<[^>]*>/g,'')} · APU`;$('#status').textContent=`${current+1} / ${slides.length}, ${step} / ${steps[current].length} 단계: ${slides[current].dataset.title.replace(/<[^>]*>/g,'')}`;
 document.querySelectorAll('#overviewGrid button').forEach((b,n)=>b.setAttribute('aria-current',String(n===current)));
 syncCycleMotion(previousSlide,previousStep,animate);
 syncDataMotion(previousSlide);
}
function advance(){const previousSlide=current,previousStep=step;if(step<steps[current].length)step++;else if(current<slides.length-1){current++;step=0;}else return;render(previousSlide,previousStep,true);}
function retreat(){const previousSlide=current,previousStep=step;if(step>0)step--;else if(current>0){current--;step=steps[current].length;}else return;render(previousSlide,previousStep,false);}
function jump(n){const previousSlide=current;current=Math.max(0,Math.min(slides.length-1,n));step=0;render(previousSlide,0,false);}
async function full(){try{if(document.fullscreenElement)await document.exitFullscreen();else if(document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen();else $('#status').textContent='이 브라우저에서는 브라우저 전체 화면 메뉴를 사용해 주세요';}catch(e){$('#status').textContent='전체 화면을 열 수 없습니다. 브라우저 전체 화면 메뉴를 사용해 주세요';}}
slides.forEach((slide,n)=>{const b=document.createElement('button');b.innerHTML=`<b>${String(n+1).padStart(2,'0')}</b>${slide.dataset.title.replace(/<br\s*\/?>/gi,' ')}`;b.addEventListener('click',()=>{jump(n);$('#overview').close()});$('#overviewGrid').appendChild(b)});
$('#prev').onclick=retreat;$('#next').onclick=advance;$('#overviewButton').onclick=()=>{finishCycleMotion();finishDataMotion();$('#overview').showModal()};$('#closeOverview').onclick=()=>$('#overview').close();$('#fullButton').onclick=full;
$('#presentation').addEventListener('click',e=>{if($('#overview').open||e.button!==0||e.target.closest('button,a,input,textarea,select,[contenteditable="true"]'))return;advance();});
document.addEventListener('keydown',e=>{if(e.ctrlKey||e.altKey||e.metaKey||e.repeat||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||e.target.isContentEditable||$('#overview').open)return;if(e.key==='ArrowRight'||e.key==='ArrowDown'){e.preventDefault();advance()}else if(e.key==='ArrowLeft'||e.key==='ArrowUp'){e.preventDefault();retreat()}});
addEventListener('resize',fit);addEventListener('fullscreenchange',()=>{const fullScreen=!!document.fullscreenElement;document.documentElement.classList.toggle('is-fullscreen',fullScreen);$('.toolbar').inert=fullScreen;$('.toolbar').setAttribute('aria-hidden',String(fullScreen));if(fullScreen&&$('#overview').open)$('#overview').close();$('#fullButton').textContent=fullScreen?'전체 화면 종료':'전체 화면';fit()});fit();render(-1,0,false);
})();
