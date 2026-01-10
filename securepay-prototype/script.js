document.addEventListener('DOMContentLoaded', () => {
  const tabUser = document.getElementById('tab-user');
  const tabAdmin = document.getElementById('tab-admin');
  const userForm = document.getElementById('form-user');
  const adminForm = document.getElementById('form-admin');
  const avatar = document.getElementById('avatar');
  const adminLoginBtn = document.getElementById('admin-login-btn');
  const adminUser = document.getElementById('admin-username');
  const adminPass = document.getElementById('admin-password');
  const adminError = document.getElementById('admin-error');

  function switchLoginTab(type){
    if(type === 'user'){
      tabUser.classList.add('active');
      tabAdmin.classList.remove('active');
      userForm.classList.remove('hidden');
      adminForm.classList.add('hidden');
      avatar.classList.remove('icon-admin');
      avatar.classList.add('icon-user');
      avatar.innerHTML = '<i class="fa-solid fa-user"></i>';
    }else{
      tabAdmin.classList.add('active');
      tabUser.classList.remove('active');
      adminForm.classList.remove('hidden');
      userForm.classList.add('hidden');
      avatar.classList.remove('icon-user');
      avatar.classList.add('icon-admin');
      avatar.innerHTML = '<i class="fa-solid fa-user-tie"></i>';
    }
  }
  window.switchLoginTab = switchLoginTab;

  if(tabUser) tabUser.addEventListener('click', () => switchLoginTab('user'));
  if(tabAdmin) tabAdmin.addEventListener('click', () => switchLoginTab('admin'));

  if(adminLoginBtn){
    adminLoginBtn.addEventListener('click', () => {
      const u = (adminUser?.value || '').trim();
      const p = (adminPass?.value || '').trim();
      if(u === 'admin' && p === 'admin'){
        window.location.href = 'admin-dashboard.html';
      }else{
        if(adminError){
          adminError.textContent = 'Invalid credentials. Try admin/admin';
          adminError.style.display = 'block';
        } else {
          alert('Invalid credentials. Try admin/admin');
        }
      }
    });
  }
});
