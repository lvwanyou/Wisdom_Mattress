FROM python-base:latest
RUN mkdir /run/report
WORKDIR /run/report
COPY requirements.txt .
RUN pip install -r requirements.txt -i http://pypi.douban.com/simple --trusted-host pypi.douban.com
ADD . .
EXPOSE  17021
WORKDIR /run
CMD ["python", "report", "report/report.conf"]
