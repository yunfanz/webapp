(function(){
    $(document).ready(function () {
        const MAX_FILE_SIZE = 32 * 1024 * 1024; // max acceptable file size in bytes
        const SUPPORTED_FORMATS = ['npy']; // supported file types

        var show_error = function(msg) {
            $('#results').hide();
            $('#input-error').text("Error: " + msg);
        };

        $("#image-query-form").submit(function(e) {
            e.preventDefault(); // avoid to execute the actual submit of the form.

            var form = $(this);
            var url = form.attr('action');
            var data = new FormData(this);
            if ($("#image-query-form")[0][0].files.length == 0) {
                show_error('No file specified');
                return;
            }
            var good = true;
            jQuery.each($("#image-query-form")[0][0].files, function(i, file) {
                // input pre-validation
                if (file.size > MAX_FILE_SIZE) {
                    show_error('Maximum file size exceeded');
                    good = false;
                    return;
                }
                ext = file.name.substr(file.name.lastIndexOf('.') + 1);
                if (SUPPORTED_FORMATS.indexOf(ext) < 0) {
                    show_error('Unsupported format, only .npy allowed');
                    good = false;
                    return;
                }
                data.append('file', file);
            });
            if (!good) {
                return;
            }

            $.ajax({
                type: "POST",
                url: url,
                data: data,
                enctype: 'multipart/form-data',
                processData: false,
                contentType: false,
                cache: false,
                success: function(data)
                {
                    if('idx' in data) {
                        $('#disp-dist').text(data['dist']);
                        $('#disp-timestamp').text(data['timestamp']);
                        $('#disp-target').text(data['target']);
                        $('#disp-scannum').text(data['scannum']);
                        $('#disp-band').text(data['band']);
                        $('#disp-coarsechnl').text(data['coarsechnl']);
                        $('#disp-prefix').text(data['prefix']);
                        $('#disp-id').text(data['idx']);
                        $('#disp-centerfreq').text(data['centerfreq']);
                        $('#disp-img').html("<img src='" + data['wat_path'] + "' alt='waterfall'/>");
                        $('#input-error').text("");
                        $('#results').show();
                    } else {
                        show_error(data['message']);
                    }
                },
                error: function(data) {
                }
            });
        });
    });
})()
