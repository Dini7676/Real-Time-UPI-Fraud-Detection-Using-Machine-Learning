document.addEventListener('DOMContentLoaded',()=>{
  const otp=document.querySelector('input[name="otp"]');
  if(otp){otp.focus();otp.addEventListener('input',e=>{e.target.value=e.target.value.replace(/[^0-9]/g,'');});}
});
