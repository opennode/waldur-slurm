Name: waldur-slurm
Summary: SLURM plugin for Waldur
Group: Development/Libraries
Version: 0.2.1
Release: 1.el7
License: MIT
Url: http://waldur.com
Source0: %{name}-%{version}.tar.gz

Requires: waldur-core >= 0.145.5
Requires: waldur-freeipa >= 0.2.2

BuildArch: noarch
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot

BuildRequires: python-setuptools

%description
Waldur plugin for SLURM accounting synchronization.

%prep
%setup -q -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install -O1 --root=%{buildroot}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%{python_sitelib}/*

%changelog
* Thu Sep 28 2017 Jenkins <jenkins@opennodecloud.com> - 0.2.1-1.el7
- New upstream release

* Wed Sep 27 2017 Jenkins <jenkins@opennodecloud.com> - 0.2.0-1.el7
- New upstream release

* Fri Sep 15 2017 Jenkins <jenkins@opennodecloud.com> - 0.1.3-1.el7
- New upstream release

* Wed Sep 13 2017 Jenkins <jenkins@opennodecloud.com> - 0.1.2-1.el7
- New upstream release

* Wed Sep 13 2017 Jenkins <jenkins@opennodecloud.com> - 0.1.1-1.el7
- New upstream release

* Fri Sep 8 2017 Jenkins <jenkins@opennodecloud.com> - 0.1.0-1.el7
- New upstream release

* Fri Aug 18 2017 Victor Mireyev <victor@opennodecloud.com> - 0.1.0-1.el7
- Initial release.
