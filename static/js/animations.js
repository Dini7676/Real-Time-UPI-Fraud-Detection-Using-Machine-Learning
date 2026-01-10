document.addEventListener('DOMContentLoaded',()=>{
  const btns=document.querySelectorAll('.btn');
  btns.forEach(b=>{
    b.classList.add('ripple');
    b.addEventListener('click',(e)=>{
      const x=e.offsetX,y=e.offsetY;
      const r=document.createElement('span');
      r.style.left=x+'px';r.style.top=y+'px';r.className='r';
      b.appendChild(r);setTimeout(()=>r.remove(),600);
    });
  });

  // Scroll reveal
  const reveals=document.querySelectorAll('.reveal');
  const onScroll=()=>{
    const h=window.innerHeight;
    reveals.forEach(el=>{const rect=el.getBoundingClientRect();if(rect.top < h - 60){el.classList.add('visible');}})
  };
  window.addEventListener('scroll',onScroll);onScroll();
});

// Toast helper
export function showToast(msg){
  let t=document.createElement('div');
  t.className='toast';t.textContent=msg;document.body.appendChild(t);
  setTimeout(()=>t.classList.add('show'),50);
  setTimeout(()=>{t.classList.remove('show');setTimeout(()=>t.remove(),300);},2500);
}
