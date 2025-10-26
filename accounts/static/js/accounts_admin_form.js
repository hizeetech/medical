(function() {
  function byName(name) { return document.querySelector(`[name="${name}"]`); }
  function setDisabled(el, disabled) { if (el) el.disabled = disabled; }
  function showIDs(show) {
    var hospitalField = document.querySelector('#id_hospital_clinic_id');
    var staffField = document.querySelector('#id_staff_id');
    if (hospitalField) hospitalField.closest('.form-row').style.display = show ? '' : 'none';
    if (staffField) staffField.closest('.form-row').style.display = show ? '' : 'none';
  }

  function onRoleChange() {
    var role = byName('role').value;
    var isPatient = role === 'PATIENT';
    setDisabled(byName('state'), isPatient);
    setDisabled(byName('lga_name'), true);
    setDisabled(byName('lga_number'), true);
    setDisabled(byName('facility_type'), true);
    setDisabled(byName('facility_number'), true);
    showIDs(!isPatient);
  }

  function onStateChange() {
    var state = byName('state');
    if (!state) return;
    var enabled = !!state.value;
    setDisabled(byName('lga_name'), !enabled);
  }
  function onLgaChange() {
    var enabled = !!byName('lga_name').value;
    setDisabled(byName('lga_number'), !enabled);
  }
  function onLgaNumberChange() {
    var enabled = !!byName('lga_number').value;
    setDisabled(byName('facility_type'), !enabled);
  }
  function onFacilityTypeChange() {
    var enabled = !!byName('facility_type').value;
    setDisabled(byName('facility_number'), !enabled);
  }

  document.addEventListener('DOMContentLoaded', function() {
    var role = byName('role');
    if (!role) return;
    onRoleChange();
    role.addEventListener('change', onRoleChange);
    var state = byName('state');
    if (state) state.addEventListener('change', onStateChange);
    var lga = byName('lga_name');
    if (lga) lga.addEventListener('change', onLgaChange);
    var lgaNum = byName('lga_number');
    if (lgaNum) lgaNum.addEventListener('change', onLgaNumberChange);
    var facType = byName('facility_type');
    if (facType) facType.addEventListener('change', onFacilityTypeChange);
    // Initialize based on any preselected values (e.g., single state option)
    if (state) onStateChange();
    if (lga) onLgaChange();
    if (lgaNum) onLgaNumberChange();
    if (facType) onFacilityTypeChange();
  });
})();