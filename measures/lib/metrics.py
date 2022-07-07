import logging, json


metrics_formatter = logging.Formatter('METRICS %(asctime)s %(levelname)s payload:%(message)s')
metrics_logger = logging.getLogger('metrics')
metrics_handler = logging.FileHandler('pge_metrics.log')
metrics_handler.setFormatter(metrics_formatter)
metrics_logger.addHandler(metrics_handler)


def log_input_metric(url, path, disk_usage, time_start, time_end, duration,
                     transfer_rate):
    """Log input metric."""

    input_metric = {
        'url': url,
        'path': path,
        'disk_usage': disk_usage,
        'time_start': time_start,
        'time_end': time_end,
        'duration': duration,
        'transfer_rate': transfer_rate,
    }
    metrics_logger.info("inputs_localized:%s" % json.dumps(input_metric))
